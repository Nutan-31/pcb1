from fastapi import FastAPI
from pydantic import BaseModel
import requests
import json
import re
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO

app = FastAPI()

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

class PromptRequest(BaseModel):
    prompt: str


def _split_ref_pin(value: str):
    """Parse values like R1:1 or D1-A into (ref, pin)."""
    if not value:
        return None, None
    text = str(value).strip()
    match = re.match(r'^([A-Za-z]+\d+)[\s:\-_/]*([A-Za-z0-9+\-]+)?$', text)
    if not match:
        return None, None
    ref = match.group(1).upper()
    pin = (match.group(2) or "").upper()
    return ref, pin


def _parse_connection_line(text: str):
    """Parse connection text like 'R1 pin 1 to D1 pin 2'."""
    if not text:
        return None

    pattern = (
        r'([A-Za-z]+\d+)\s*(?:pin|pad)?\s*([A-Za-z0-9+\-]*)\s*'
        r'(?:to|->|connect(?:ed)?\s*to)\s*'
        r'([A-Za-z]+\d+)\s*(?:pin|pad)?\s*([A-Za-z0-9+\-]*)'
    )
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None

    return {
        "from_ref": match.group(1).upper(),
        "from_pin": (match.group(2) or "").upper(),
        "to_ref": match.group(3).upper(),
        "to_pin": (match.group(4) or "").upper(),
    }


def ensure_connections(circuit_data: dict) -> dict:
    """Normalize connection objects and create a fallback chain if missing."""
    if not circuit_data:
        return circuit_data

    components = circuit_data.get("components", [])
    raw_connections = circuit_data.get("connections", []) or []
    normalized = []

    for item in raw_connections:
        conn = None

        if isinstance(item, dict):
            from_ref = (item.get("from_ref") or "").upper()
            to_ref = (item.get("to_ref") or "").upper()
            from_pin = (item.get("from_pin") or "").upper()
            to_pin = (item.get("to_pin") or "").upper()

            if not (from_ref and to_ref):
                from_value = item.get("from")
                to_value = item.get("to")
                if isinstance(from_value, str) and isinstance(to_value, str):
                    from_ref, from_pin = _split_ref_pin(from_value)
                    to_ref, to_pin = _split_ref_pin(to_value)

            if from_ref and to_ref:
                conn = {
                    "from_ref": from_ref,
                    "from_pin": from_pin,
                    "to_ref": to_ref,
                    "to_pin": to_pin,
                    "net_name": item.get("net_name") or ""
                }

        elif isinstance(item, str):
            parsed = _parse_connection_line(item)
            if parsed:
                conn = {
                    **parsed,
                    "net_name": ""
                }

        if conn:
            normalized.append(conn)

    if not normalized:
        refs = [c.get("ref", "").upper() for c in components if c.get("ref")]
        refs = [r for r in refs if r]
        for i in range(max(0, len(refs) - 1)):
            normalized.append({
                "from_ref": refs[i],
                "from_pin": "2",
                "to_ref": refs[i + 1],
                "to_pin": "1",
                "net_name": f"NET_{i + 1}"
            })

    for idx, conn in enumerate(normalized, start=1):
        if not conn.get("net_name"):
            conn["net_name"] = f"NET_{idx}"

    circuit_data["connections"] = normalized
    return circuit_data

def query_ollama(prompt: str) -> str:
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": "deepseek-coder:6.7b",
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        )
        data = response.json()
        return data.get("response", "No response received")
    except Exception as e:
        return f"Error querying Ollama: {str(e)}"

def validate_and_fix_circuit(circuit_data: dict) -> dict:
    """Post-process circuit data to fix common mistakes"""
    if not circuit_data:
        return circuit_data

    components = circuit_data.get("components", [])

    # Check if LED exists
    has_led = any(
        "LED" in c.get("type", "").upper() or
        "LED" in c.get("value", "").upper()
        for c in components
    )

    # Check if LED resistor exists
    has_led_resistor = any(
        "LED" in c.get("description", "").upper() and
        c.get("type", "").upper() == "R"
        for c in components
    )

    # Add LED resistor if missing
    if has_led and not has_led_resistor:
        r_nums = [int(c["ref"][1:]) for c in components
                  if c.get("ref", "").startswith("R") and
                  c["ref"][1:].isdigit()]
        next_r = max(r_nums) + 1 if r_nums else 1
        components.append({
            "ref": f"R{next_r}",
            "type": "R",
            "value": "330R",
            "description": "LED current limiting resistor"
        })

    # Check if IC exists
    has_ic = any(
        c.get("type", "").upper() in ["U", "IC"]
        for c in components
    )

    # Check if decoupling cap exists
    has_decoupling = any(
        "DECOUPL" in c.get("description", "").upper() or
        "BYPASS" in c.get("description", "").upper()
        for c in components
    )

    # Add decoupling cap if missing
    if has_ic and not has_decoupling:
        c_nums = [int(c["ref"][1:]) for c in components
                  if c.get("ref", "").startswith("C") and
                  c["ref"][1:].isdigit()]
        next_c = max(c_nums) + 1 if c_nums else 1
        components.append({
            "ref": f"C{next_c}",
            "type": "C",
            "value": "100nF",
            "description": "Decoupling capacitor"
        })

    circuit_data["components"] = components
    circuit_data = ensure_connections(circuit_data)
    return circuit_data

@app.post("/generate_schematic")
def generate_schematic(request: PromptRequest):
    try:
        prompt = f"""You are an expert electronics engineer with 20 years experience.

Task: Generate a COMPLETE and CORRECT component list for: {request.prompt}

STRICT RULES:
1. For 555 timer circuits: ALWAYS use NE555, NEVER use 74LS74 or other ICs
2. For LED circuits: ALWAYS include current limiting resistor 220R to 470R
3. For timing circuits: Use correct capacitor values 10uF to 100uF for visible blink
4. For 555 astable: Need TWO timing resistors + ONE timing capacitor + ONE decoupling cap
5. Always include decoupling capacitors 100nF near ICs
6. Use realistic component values that actually work
7. For Arduino circuits: Include crystal, decoupling caps, reset circuit
8. For power supply circuits: Include input and output capacitors
9. For amplifier circuits: Include coupling capacitors and bias resistors
10. For any circuit with LED: ALWAYS add current limiting resistor 330R

Return ONLY valid JSON with no explanation:
{{
    "circuit_name": "Exact circuit name",
    "description": "How this circuit works",
    "components": [
        {{"ref": "U1", "type": "U", "value": "CORRECT_IC", "description": "Main IC"}},
        {{"ref": "R1", "type": "R", "value": "CORRECT_VALUE", "description": "Purpose"}},
        {{"ref": "R2", "type": "R", "value": "CORRECT_VALUE", "description": "Purpose"}},
        {{"ref": "C1", "type": "C", "value": "CORRECT_VALUE", "description": "Purpose"}},
        {{"ref": "D1", "type": "LED", "value": "LED", "description": "Purpose"}}
    ],
    "connections": [
        {{"from_ref": "R1", "from_pin": "1", "to_ref": "D1", "to_pin": "1", "net_name": "LED_SIGNAL"}},
        {{"from_ref": "R1", "from_pin": "2", "to_ref": "BT1", "to_pin": "1", "net_name": "VCC"}},
        {{"from_ref": "D1", "from_pin": "2", "to_ref": "BT1", "to_pin": "2", "net_name": "GND"}}
    ],
    "voltage": "5V"
}}

Return ONLY the JSON object. No markdown. No explanation."""

        ai_response = query_ollama(prompt)

        json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
        if json_match:
            try:
                circuit_data = json.loads(json_match.group())
                circuit_data = validate_and_fix_circuit(circuit_data)
                return {
                    "result": f"Circuit: {circuit_data.get('circuit_name', 'Unknown')}\nComponents: {len(circuit_data.get('components', []))}",
                    "circuit_data": circuit_data,
                    "ai_response": ai_response
                }
            except:
                pass

        return {
            "result": ai_response,
            "circuit_data": None,
            "ai_response": ai_response
        }

    except Exception as e:
        return {
            "result": f"Error: {str(e)}",
            "circuit_data": None,
            "ai_response": ""
        }

@app.post("/write_schematic")
def write_schematic(request: PromptRequest):
    try:
        prompt = f"""List the electronic components needed for: {request.prompt}

Format your response as a simple list like:
- LED
- Resistor 330 ohm
- Battery 9V
- Capacitor 100nF

Only list components, nothing else."""

        ai_response = query_ollama(prompt)
        return {
            "result": f"Components identified:\n{ai_response}",
            "ai_response": ai_response
        }
    except Exception as e:
        return {"result": f"Error: {str(e)}", "ai_response": ""}

@app.post("/generate_netlist")
def generate_netlist(request: PromptRequest):
    try:
        prompt = f"""List the electronic components and their connections for: {request.prompt}

Format your response like this:
Components:
- LED (anode, cathode)
- Resistor 330 ohm
- Battery 9V

Connections:
- Connect LED anode to Resistor pin 1
- Connect Resistor pin 2 to Battery positive
- Connect LED cathode to Battery negative (GND)

Only list components and connections, nothing else."""

        ai_response = query_ollama(prompt)
        return {
            "result": f"Netlist data generated!\n{ai_response}",
            "ai_response": ai_response
        }
    except Exception as e:
        return {"result": f"Error: {str(e)}", "ai_response": ""}

@app.post("/suggest_placement")
def suggest_placement(request: PromptRequest):
    prompt = f"You are a PCB layout expert. Suggest optimal component placement for: {request.prompt}"
    result = query_ollama(prompt)
    return {"result": result}

@app.post("/check_manufacturing")
def check_manufacturing(request: PromptRequest):
    prompt = f"""You are a PCB design rules expert.
Analyze these PCB specifications and list any potential issues:
{request.prompt}

Check for:
1. Trace width violations (minimum 0.1mm)
2. Clearance violations (minimum 0.2mm)
3. Drill size issues (minimum 0.2mm)
4. Layer stack up issues
5. Signal integrity concerns

List each issue found with severity (ERROR/WARNING)."""
    result = query_ollama(prompt)
    return {"result": result}

@app.post("/run_drc")
def run_drc(request: PromptRequest):
    try:
        prompt = f"""You are a PCB design rules expert.
Write a DRC analysis for this PCB: {request.prompt}

Respond with only this format:

DRC REPORT
==========
ERROR: Trace width violation - minimum should be 0.15mm
ERROR: Missing board outline on Edge.Cuts layer
WARNING: No courtyard defined for components
WARNING: Silkscreen may overlap pads
INFO: Board has 2 layers
INFO: Clearance rules check complete

RESULT: FAIL
Total Errors: 2
Total Warnings: 2

FIXES:
1. Increase trace width to 0.15mm minimum
2. Add board outline on Edge.Cuts layer
3. Add courtyard to all footprints
4. Check silkscreen clearance"""

        result = query_ollama(prompt)
        return {"result": result}
    except Exception as e:
        return {"result": f"DRC Error: {str(e)}"}

@app.post("/rl_placement")
def rl_placement(request: PromptRequest):
    try:
        num_components = 4

        class PCBEnv(gym.Env):
            def __init__(self):
                super().__init__()
                self.action_space = spaces.Box(
                    low=0, high=1, shape=(2,), dtype=np.float32)
                self.observation_space = spaces.Box(
                    low=0, high=1, shape=(num_components * 2,), dtype=np.float32)
                self.positions = np.zeros((num_components, 2))
                self.current = 0

            def reset(self, seed=None):
                super().reset(seed=seed)
                self.positions = np.zeros((num_components, 2))
                self.current = 0
                return self.positions.flatten().astype(np.float32), {}

            def step(self, action):
                self.positions[self.current] = action
                self.current += 1
                done = self.current >= num_components
                return self.positions.flatten().astype(np.float32), 1.0, done, False, {}

        env = PCBEnv()
        model = PPO("MlpPolicy", env, verbose=0)
        model.learn(total_timesteps=100)

        obs, _ = env.reset()
        placements = []
        for _ in range(num_components):
            action, _ = model.predict(obs)
            obs, _, done, _, _ = env.step(action)
            placements.append({
                "x": float(action[0] * 100),
                "y": float(action[1] * 100)
            })
            if done:
                break

        return {
            "result": f"RL Placement calculated for {num_components} components!",
            "placements": placements
        }

    except Exception as e:
        return {"result": f"Error: {str(e)}", "placements": []}

@app.post("/onnx_placement")
def onnx_placement(request: PromptRequest):
    try:
        import sys
        plugin_dir = "C:\\Users\\B T NUTAN REDDY\\Documents\\KiCad\\9.0\\scripting\\plugins\\ai_kicad_plugin"
        if plugin_dir not in sys.path:
            sys.path.insert(0, plugin_dir)

        from onnx_placement import train_and_export_onnx
        success = train_and_export_onnx(num_components=10, timesteps=500)

        if success:
            return {"result": "ONNX model trained and exported successfully!"}
        else:
            return {"result": "ONNX export failed but model saved!"}

    except Exception as e:
        return {"result": f"Error: {str(e)}"}

@app.post("/export_schematic")
def export_schematic(request: PromptRequest):
    try:
        prompt = f"""You are an expert electronics engineer.
Generate a COMPLETE component list for: {request.prompt}

Return ONLY this JSON format with no explanation:
{{
    "circuit_name": "Circuit Name",
    "description": "Brief description",
    "components": [
        {{"ref": "R1", "type": "R", "value": "10K"}},
        {{"ref": "C1", "type": "C", "value": "100nF"}},
        {{"ref": "D1", "type": "LED", "value": "LED"}}
    ],
    "connections": [
        {{"from_ref": "R1", "from_pin": "1", "to_ref": "D1", "to_pin": "1", "net_name": "LED_SIGNAL"}},
        {{"from_ref": "R1", "from_pin": "2", "to_ref": "BT1", "to_pin": "1", "net_name": "VCC"}},
        {{"from_ref": "D1", "from_pin": "2", "to_ref": "BT1", "to_pin": "2", "net_name": "GND"}}
    ],
    "voltage": "5V"
}}"""

        ai_response = query_ollama(prompt)

        circuit_data = None
        json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
        if json_match:
            try:
                circuit_data = json.loads(json_match.group())
                circuit_data = validate_and_fix_circuit(circuit_data)
            except:
                pass

        if not circuit_data:
            return {"result": "Could not parse circuit data!", "circuit_data": None}

        return {
            "result": f"Circuit data ready: {circuit_data.get('circuit_name')}",
            "circuit_data": circuit_data
        }

    except Exception as e:
        return {"result": f"Error: {str(e)}", "circuit_data": None}

@app.get("/health")
def health():
    return {"status": "running"}