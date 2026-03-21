from fastapi import FastAPI
from pydantic import BaseModel
import requests
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
    prompt = f"You are a PCB schematic expert. Generate KiCad schematic instructions for: {request.prompt}. Return component list and connections."
    result = query_ollama(prompt)
    return {"result": result}

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

@app.post("/rl_placement")
def rl_placement(request: PromptRequest):
    try:
        # Run RL placement in FastAPI (outside KiCad)
        num_components = 4  # default

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

        # Get placements
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
    
@app.post("/write_schematic")
def write_schematic(request: PromptRequest):
    try:
        # First get AI response
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
    
@app.get("/health")
def health():
    return {"status": "running"}