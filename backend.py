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

@app.post("/generate_schematic")
def generate_schematic(request: PromptRequest):
    try:
        prompt = f"""List electronic components for: {request.prompt}

Return ONLY this JSON format:
{{
    "circuit_name": "Circuit Name",
    "description": "Brief description",
    "components": [
        {{"ref": "R1", "type": "R", "value": "10K"}},
        {{"ref": "C1", "type": "C", "value": "100nF"}},
        {{"ref": "D1", "type": "LED", "value": "LED"}},
        {{"ref": "Q1", "type": "Q", "value": "NPN"}},
        {{"ref": "U1", "type": "U", "value": "NE555"}}
    ],
    "connections": [],
    "voltage": "5V"
}}

For {request.prompt}, replace the example components with the actual components needed."""

        ai_response = query_ollama(prompt)
        
        json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
        if json_match:
            try:
                circuit_data = json.loads(json_match.group())
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
        prompt = f"""You are a Python programmer. 
Write a DRC analysis as a Python dictionary for this PCB: {request.prompt}

Respond with only this text format, no explanation:

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
                self.action_space = spaces.Box(low=0, high=1, shape=(2,), dtype=np.float32)
                self.observation_space = spaces.Box(low=0, high=1, shape=(num_components * 2,), dtype=np.float32)
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
            return {"result": "✅ ONNX model trained and exported successfully!"}
        else:
            return {"result": "⚠️ ONNX export failed but model saved!"}
            
    except Exception as e:
        return {"result": f"Error: {str(e)}"}
    
@app.post("/export_schematic")
def export_schematic(request: PromptRequest):
    try:
        # First generate circuit data
        prompt = f"""List electronic components for: {request.prompt}

Return ONLY this JSON format:
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
            except:
                pass

        if not circuit_data:
            return {"result": "Could not parse circuit data from AI response!"}

        return {
            "result": f"Circuit data ready: {circuit_data.get('circuit_name')}",
            "circuit_data": circuit_data
        }

    except Exception as e:
        return {"result": f"Error: {str(e)}", "circuit_data": None}

@app.get("/health")
def health():
    return {"status": "running"}