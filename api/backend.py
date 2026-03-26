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

def query_ollama(prompt: str) -> str:
    try:
        wrapped_prompt = f"""You are an expert electronics engineer and PCB designer.
You must always provide helpful answers about electronic circuits and components.
Never refuse to answer electronics questions.

{prompt}

Provide a complete and detailed answer."""

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": "deepseek-coder:6.7b",
                "prompt": wrapped_prompt,
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

    has_led = any(
        "LED" in c.get("type", "").upper() or
        "LED" in c.get("value", "").upper()
        for c in components
    )

    has_led_resistor = any(
        "LED" in c.get("description", "").upper() and
        c.get("type", "").upper() == "R"
        for c in components
    )

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

    has_ic = any(
        c.get("type", "").upper() in ["U", "IC"]
        for c in components
    )

    has_decoupling = any(
        "DECOUPL" in c.get("description", "").upper() or
        "BYPASS" in c.get("description", "").upper()
        for c in components
    )

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
    return circuit_data

def generate_fallback_circuit(prompt: str) -> dict:
    """Generate circuit data based on keywords when AI fails"""
    prompt_lower = prompt.lower()
    components = []
    circuit_name = prompt.title()
    voltage = "5V"

    comp_num = {"R": 1, "C": 1, "D": 1, "U": 1, "Q": 1, "SW": 1, "Y": 1, "BT": 1}

    def add_comp(type_, value, desc):
        ref = f"{type_}{comp_num[type_]}"
        comp_num[type_] += 1
        components.append({
            "ref": ref,
            "type": type_,
            "value": value,
            "description": desc
        })

    if "9v" in prompt_lower or "battery" in prompt_lower:
        voltage = "9V"
    elif "12v" in prompt_lower:
        voltage = "12V"
    elif "3.3v" in prompt_lower:
        voltage = "3.3V"

    if "555" in prompt_lower:
        add_comp("U", "NE555", "555 Timer IC")
        add_comp("R", "10K", "Timing resistor 1")
        add_comp("R", "100K", "Timing resistor 2")
        add_comp("C", "10uF", "Timing capacitor")
        add_comp("C", "100nF", "Decoupling capacitor")
    elif "arduino" in prompt_lower:
        add_comp("U", "ATmega328P", "Arduino MCU")
        add_comp("Y", "16MHz", "Crystal")
        add_comp("C", "22pF", "Crystal capacitor 1")
        add_comp("C", "22pF", "Crystal capacitor 2")
        add_comp("C", "100nF", "Decoupling capacitor")
        add_comp("R", "10K", "Reset pullup")
    elif "esp32" in prompt_lower:
        add_comp("U", "ESP32", "ESP32 module")
        add_comp("C", "100uF", "Power capacitor")
        add_comp("C", "100nF", "Decoupling capacitor")
        add_comp("R", "10K", "Pullup resistor")
    elif "regulator" in prompt_lower or "3.3v" in prompt_lower:
        add_comp("U", "AMS1117-3.3", "LDO Regulator")
        add_comp("C", "10uF", "Input capacitor")
        add_comp("C", "10uF", "Output capacitor")
        add_comp("C", "100nF", "Input decoupling")
        add_comp("C", "100nF", "Output decoupling")
    elif "mosfet" in prompt_lower:
        add_comp("Q", "2N7000", "N-channel MOSFET")
        add_comp("R", "10K", "Gate resistor")
        add_comp("R", "100K", "Gate pulldown")
        add_comp("D", "1N4007", "Flyback diode")
    elif "amplifier" in prompt_lower or "op amp" in prompt_lower:
        add_comp("U", "LM741", "Op-Amp IC")
        add_comp("R", "10K", "Input resistor")
        add_comp("R", "10K", "Feedback resistor")
        add_comp("C", "100nF", "Decoupling 1")
        add_comp("C", "100nF", "Decoupling 2")
        voltage = "12V"
    elif "temperature" in prompt_lower:
        add_comp("U", "LM35", "Temperature sensor IC")
        add_comp("R", "10K", "Pullup resistor")
        add_comp("C", "100nF", "Decoupling capacitor")
    elif "bluetooth" in prompt_lower:
        add_comp("U", "HC-05", "Bluetooth module")
        add_comp("R", "1K", "TX voltage divider 1")
        add_comp("R", "2K", "TX voltage divider 2")
        add_comp("C", "100nF", "Decoupling capacitor")
    elif "motor" in prompt_lower:
        add_comp("U", "L298N", "Motor driver IC")
        add_comp("C", "100nF", "Decoupling capacitor")
        add_comp("D", "1N4007", "Flyback diode 1")
        add_comp("D", "1N4007", "Flyback diode 2")
    elif "sensor" in prompt_lower:
        add_comp("U", "LM358", "Op-Amp for sensor")
        add_comp("R", "10K", "Sensor pullup")
        add_comp("R", "10K", "Voltage divider")
        add_comp("C", "100nF", "Decoupling capacitor")
    elif "power" in prompt_lower or "supply" in prompt_lower:
        add_comp("U", "LM7805", "5V Voltage regulator")
        add_comp("C", "100uF", "Input capacitor")
        add_comp("C", "100uF", "Output capacitor")
        add_comp("C", "100nF", "Input decoupling")
        add_comp("C", "100nF", "Output decoupling")
        add_comp("D", "1N4007", "Rectifier diode")
    elif "relay" in prompt_lower:
        add_comp("Q", "BC547", "NPN transistor")
        add_comp("R", "1K", "Base resistor")
        add_comp("D", "1N4007", "Flyback diode")
        add_comp("U", "RELAY", "5V Relay")
    else:
        add_comp("R", "10K", "Resistor")
        add_comp("C", "100nF", "Capacitor")

    if "led" in prompt_lower:
        add_comp("D", "LED", "Status LED")
        add_comp("R", "330R", "LED current limiting")

    if "switch" in prompt_lower or "button" in prompt_lower:
        add_comp("SW", "SW_PUSH", "Push button")
        add_comp("R", "10K", "Button pullup")

    if not components:
        add_comp("R", "10K", "Resistor")
        add_comp("C", "100nF", "Capacitor")

    return {
        "circuit_name": circuit_name,
        "description": f"Circuit for {prompt}",
        "components": components,
        "connections": [],
        "voltage": voltage
    }

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
    "connections": [],
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

        # AI failed - use smart fallback
        fallback_data = generate_fallback_circuit(request.prompt)
        return {
            "result": f"Circuit: {fallback_data.get('circuit_name')}\nComponents: {len(fallback_data.get('components', []))}",
            "circuit_data": fallback_data,
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
    "connections": [],
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
            circuit_data = generate_fallback_circuit(request.prompt)

        return {
            "result": f"Circuit data ready: {circuit_data.get('circuit_name')}",
            "circuit_data": circuit_data
        }

    except Exception as e:
        return {"result": f"Error: {str(e)}", "circuit_data": None}

@app.get("/health")
def health():
    return {"status": "running"}