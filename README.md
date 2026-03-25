# 🤖 AI-Powered KiCad Plugin

A local-first AI automation tool that uses LLMs and Reinforcement Learning to automate PCB design directly within KiCad.

**100% Private • No Cloud • No API Keys Required**

---

## 🎯 Features

| Feature | Description |
|---|---|
| 📐 Auto Generate Schematic | Generate circuit schematics from natural language |
| ✏️ Write Components to PCB | Automatically add components to PCB board |
| 🔗 Generate Netlist | Auto-generate KiCad netlist files |
| 🧠 AI Component Placement | RL-based optimal component placement |
| ⚡ ONNX Placement | Fast pre-trained model placement |
| 🔧 Manufacturing Checks | AI-powered DFM analysis |
| ✅ DRC Check | Design Rule Check with AI analysis |
| 📦 Export Gerber Files | Auto-export all manufacturing files |
| 📄 Export .kicad_sch | Export circuit as KiCad schematic |
| 🔀 Auto Route (FreeRouting) | Automatic PCB trace routing |

---

## 🏗️ System Architecture
```
User Input (Natural Language)
        ↓
KiCad Plugin UI (plugin.py)
        ↓
FastAPI Backend (backend.py) → port 8000
        ↓
    ┌───────────────────┐
    │                   │
Ollama LLM          RL Model
(DeepSeek 6.7b)  (Stable Baselines3)
    │                   │
    └───────────────────┘
        ↓
   KiCad pcbnew API
        ↓
  PCB Design Output
```

---

## 🔧 System Requirements

| Requirement | Version |
|---|---|
| KiCad | 9.0 |
| Python | 3.12+ |
| OS | Windows 10/11 |
| Ollama | Latest |
| Java | 21+ (for FreeRouting) |

---

## ⚡ Quick Start

### Step 1 — Install Dependencies
```bash
python -m pip install anthropic stable-baselines3 gymnasium torch numpy shapely fastapi uvicorn requests onnx onnxruntime
```

### Step 2 — Install Ollama
Download from: https://ollama.com

Then pull DeepSeek model:
```bash
ollama pull deepseek-coder:6.7b
```

### Step 3 — Install Plugin
Copy plugin folder to:
```
C:\Users\{username}\AppData\Roaming\kicad\9.0\scripting\plugins\ai_kicad_plugin\
```

### Step 4 — Start Everything
Double click `start_ai_plugin.bat` on Desktop!

Or manually:
```bash
# Terminal 1
ollama serve

# Terminal 2
cd ai_kicad_plugin
python -m uvicorn backend:app --reload --port 8000
```

### Step 5 — Use Plugin
1. Open KiCad PCB Editor
2. Go to **Tools → External Plugins → AI KiCad Plugin**
3. Click any feature button!

---

## 📁 Project Structure
```
ai_kicad_plugin/
│
├── plugin.py              # Main KiCad plugin UI
├── backend.py             # FastAPI backend server
├── schematic_writer.py    # Write components to PCB
├── schematic_exporter.py  # Export .kicad_sch files
├── netlist_generator.py   # Generate netlists
├── rl_placement.py        # RL component placement
├── onnx_placement.py      # ONNX fast placement
├── gerber_export.py       # Gerber file export
├── freerouting_integration.py  # FreeRouting auto-routing
├── mfg_checks.py          # Manufacturing checks
├── llm_handler.py         # LLM interface
└── __init__.py            # Package init
```

---

## 🤖 AI Pipeline

### Natural Language → PCB

1. User types circuit description
2. DeepSeek LLM generates component list as JSON
3. Components added to KiCad PCB automatically
4. RL model optimizes placement
5. FreeRouting auto-routes traces
6. DRC checks manufacturing rules
7. Gerber files exported for manufacturing!

---

## 🧠 RL Placement

Uses **Stable Baselines3 PPO** algorithm:
- Trains on board dimensions
- Optimizes component positions
- Minimizes overlaps and maximizes signal integrity
- ONNX export for fast inference

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Check server status |
| `/generate_schematic` | POST | Generate circuit from text |
| `/write_schematic` | POST | Get component list |
| `/generate_netlist` | POST | Generate netlist data |
| `/rl_placement` | POST | RL component placement |
| `/onnx_placement` | POST | ONNX fast placement |
| `/check_manufacturing` | POST | DFM analysis |
| `/run_drc` | POST | DRC check |
| `/export_schematic` | POST | Export .kicad_sch |

---

## 🔒 Privacy

- All processing happens **locally** on your machine
- No data sent to cloud services
- No API keys required
- Works completely offline!

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| LLM | DeepSeek-Coder 6.7b via Ollama |
| RL | Stable Baselines3 + Gymnasium |
| Fast Inference | ONNX Runtime |
| Backend | FastAPI + Uvicorn |
| PCB API | KiCad pcbnew Python API |
| Auto Router | FreeRouting 2.1.0 |

---

## 📝 License

MIT License — Free to use and modify!

---

## 🙏 Acknowledgements

- [KiCad](https://www.kicad.org/) — Open source PCB design
- [Ollama](https://ollama.com/) — Local LLM runtime
- [DeepSeek](https://github.com/deepseek-ai) — AI model
- [FreeRouting](https://github.com/freerouting/freerouting) — Auto router
- [Stable Baselines3](https://stable-baselines3.readthedocs.io/) — RL library