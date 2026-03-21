import pcbnew
import wx
import os
import sys
import requests

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
if PLUGIN_DIR not in sys.path:
    sys.path.insert(0, PLUGIN_DIR)

class AiKicadPlugin(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "AI KiCad Plugin"
        self.category = "AI Automation"
        self.description = "AI-Powered PCB automation using LLMs and Reinforcement Learning"
        self.show_toolbar_button = True
        self.icon_file_name = os.path.join(PLUGIN_DIR, "icon.png")

    def Run(self):
        dialog = AiPluginDialog(None)
        dialog.ShowModal()
        dialog.Destroy()


class AiPluginDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="AI KiCad Plugin", size=(450, 600))
        self.SetBackgroundColour(wx.Colour(30, 30, 30))

        panel = wx.Panel(self)
        panel.SetBackgroundColour(wx.Colour(30, 30, 30))
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Title
        title = wx.StaticText(panel, label="🤖 AI-Powered KiCad Plugin")
        title.SetForegroundColour(wx.Colour(0, 200, 255))
        title.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT,
                    wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        vbox.Add(title, flag=wx.ALIGN_CENTER | wx.TOP, border=20)

        # Subtitle
        subtitle = wx.StaticText(panel, label="Local AI • No Cloud • 100% Private")
        subtitle.SetForegroundColour(wx.Colour(150, 150, 150))
        subtitle.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT,
                    wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL))
        vbox.Add(subtitle, flag=wx.ALIGN_CENTER | wx.TOP, border=5)

        # Divider
        line = wx.StaticLine(panel)
        vbox.Add(line, flag=wx.EXPAND | wx.ALL, border=15)

        # Buttons
        btn_schematic = wx.Button(panel, label="📐  Auto Generate Schematic", size=(-1, 45))
        btn_write = wx.Button(panel, label="✏️  Write Components to PCB", size=(-1, 45))
        btn_netlist = wx.Button(panel, label="🔗  Generate Netlist", size=(-1, 45))
        btn_placement = wx.Button(panel, label="🧠  AI Component Placement (RL)", size=(-1, 45))
        btn_mfg = wx.Button(panel, label="🔧  Manufacturing Checks", size=(-1, 45))
        btn_drc = wx.Button(panel, label="✅  Run DRC Check", size=(-1, 45))

        # Button colors
        btn_schematic.SetBackgroundColour(wx.Colour(0, 120, 200))
        btn_schematic.SetForegroundColour(wx.WHITE)

        btn_write.SetBackgroundColour(wx.Colour(0, 180, 180))
        btn_write.SetForegroundColour(wx.WHITE)

        btn_netlist.SetBackgroundColour(wx.Colour(50, 50, 200))
        btn_netlist.SetForegroundColour(wx.WHITE)

        btn_placement.SetBackgroundColour(wx.Colour(0, 160, 80))
        btn_placement.SetForegroundColour(wx.WHITE)

        btn_mfg.SetBackgroundColour(wx.Colour(200, 120, 0))
        btn_mfg.SetForegroundColour(wx.WHITE)

        btn_drc.SetBackgroundColour(wx.Colour(160, 0, 160))
        btn_drc.SetForegroundColour(wx.WHITE)

        # Button fonts
        btn_font = wx.Font(10, wx.FONTFAMILY_DEFAULT,
                    wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        btn_schematic.SetFont(btn_font)
        btn_write.SetFont(btn_font)
        btn_netlist.SetFont(btn_font)
        btn_placement.SetFont(btn_font)
        btn_mfg.SetFont(btn_font)
        btn_drc.SetFont(btn_font)

        vbox.Add(btn_schematic, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border=15)
        vbox.Add(btn_write, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border=15)
        vbox.Add(btn_netlist, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border=15)
        vbox.Add(btn_placement, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border=15)
        vbox.Add(btn_mfg, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border=15)
        vbox.Add(btn_drc, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border=15)

        # Status bar
        self.status = wx.StaticText(panel, label="✅ Ready — FastAPI + Ollama Running")
        self.status.SetForegroundColour(wx.Colour(0, 200, 100))
        self.status.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT,
                    wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        vbox.Add(self.status, flag=wx.ALIGN_CENTER | wx.TOP, border=15)

        # Footer
        footer = wx.StaticText(panel, label="Powered by DeepSeek + Stable Baselines3")
        footer.SetForegroundColour(wx.Colour(100, 100, 100))
        footer.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT,
                    wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL))
        vbox.Add(footer, flag=wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, border=10)

        btn_schematic.Bind(wx.EVT_BUTTON, self.on_schematic)
        btn_write.Bind(wx.EVT_BUTTON, self.on_write)
        btn_netlist.Bind(wx.EVT_BUTTON, self.on_netlist)
        btn_placement.Bind(wx.EVT_BUTTON, self.on_placement)
        btn_mfg.Bind(wx.EVT_BUTTON, self.on_mfg)
        btn_drc.Bind(wx.EVT_BUTTON, self.on_drc)

        panel.SetSizer(vbox)

    def update_status(self, message, color=(0, 200, 100)):
        self.status.SetLabel(message)
        self.status.SetForegroundColour(wx.Colour(*color))
        self.status.Refresh()

    def on_schematic(self, event):
        input_dialog = wx.TextEntryDialog(
            self,
            "Describe your circuit:",
            "AI Schematic Generator",
            "simple LED circuit with resistor"
        )
        if input_dialog.ShowModal() == wx.ID_OK:
            prompt = input_dialog.GetValue()
            self.update_status("⏳ Generating schematic...", (255, 200, 0))
            try:
                response = requests.post(
                    "http://127.0.0.1:8000/generate_schematic",
                    json={"prompt": prompt},
                    timeout=60
                )
                result = response.json()["result"]
                self.update_status("✅ Schematic generated!", (0, 200, 100))
                wx.MessageBox(result, "AI Schematic Result", wx.OK)
            except Exception as e:
                self.update_status("❌ Error!", (255, 50, 50))
                wx.MessageBox(f"Error: {str(e)}\nMake sure FastAPI backend is running!",
                            "Error", wx.OK | wx.ICON_ERROR)
        input_dialog.Destroy()

    def on_write(self, event):
        input_dialog = wx.TextEntryDialog(
            self,
            "Describe your circuit to add components:",
            "Write Components to PCB",
            "LED circuit with resistor and battery"
        )
        if input_dialog.ShowModal() == wx.ID_OK:
            prompt = input_dialog.GetValue()
            self.update_status("⏳ Writing components to PCB...", (255, 200, 0))
            try:
                response = requests.post(
                    "http://127.0.0.1:8000/write_schematic",
                    json={"prompt": prompt},
                    timeout=60
                )
                data = response.json()
                ai_response = data.get("ai_response", "")
                from schematic_writer import write_components_from_prompt
                result = write_components_from_prompt(ai_response)
                self.update_status("✅ Components added to PCB!", (0, 200, 100))
                wx.MessageBox(result, "Components Written to PCB", wx.OK)
            except Exception as e:
                self.update_status("❌ Error!", (255, 50, 50))
                wx.MessageBox(f"Error: {str(e)}",
                            "Error", wx.OK | wx.ICON_ERROR)
        input_dialog.Destroy()

    def on_netlist(self, event):
        input_dialog = wx.TextEntryDialog(
            self,
            "Describe your circuit for netlist generation:",
            "Generate Netlist",
            "LED circuit with resistor and battery"
        )
        if input_dialog.ShowModal() == wx.ID_OK:
            prompt = input_dialog.GetValue()
            self.update_status("⏳ Generating netlist...", (255, 200, 0))
            try:
                response = requests.post(
                    "http://127.0.0.1:8000/generate_netlist",
                    json={"prompt": prompt},
                    timeout=60
                )
                data = response.json()
                ai_response = data.get("ai_response", "")
                import importlib
                import netlist_generator
                importlib.reload(netlist_generator)
                from netlist_generator import generate_netlist_from_prompt
                result = generate_netlist_from_prompt(ai_response)
                self.update_status("✅ Netlist generated!", (0, 200, 100))
                wx.MessageBox(result, "Netlist Generated", wx.OK)
            except Exception as e:
                self.update_status("❌ Error!", (255, 50, 50))
                wx.MessageBox(f"Error: {str(e)}",
                            "Error", wx.OK | wx.ICON_ERROR)
        input_dialog.Destroy()

    def on_placement(self, event):
        confirm = wx.MessageBox(
            "This will use RL to place all components on your PCB board!\n\nContinue?",
            "AI RL Placement",
            wx.YES_NO | wx.ICON_QUESTION
        )
        if confirm == wx.YES:
            self.update_status("⏳ Running RL placement...", (255, 200, 0))
            try:
                response = requests.post(
                    "http://127.0.0.1:8000/rl_placement",
                    json={"prompt": "place components"},
                    timeout=120
                )
                result = response.json()["result"]
                self.update_status("✅ Placement complete!", (0, 200, 100))
                wx.MessageBox(result, "RL Placement Result", wx.OK)
                pcbnew.Refresh()
            except Exception as e:
                self.update_status("❌ Error!", (255, 50, 50))
                wx.MessageBox(f"Error: {str(e)}\nMake sure FastAPI backend is running!",
                            "Error", wx.OK | wx.ICON_ERROR)

    def on_mfg(self, event):
        input_dialog = wx.TextEntryDialog(
            self,
            "Describe your board specifications:",
            "Manufacturing Checks",
            "2 layer board, 0.1mm trace width"
        )
        if input_dialog.ShowModal() == wx.ID_OK:
            prompt = input_dialog.GetValue()
            self.update_status("⏳ Running manufacturing checks...", (255, 200, 0))
            try:
                response = requests.post(
                    "http://127.0.0.1:8000/check_manufacturing",
                    json={"prompt": prompt},
                    timeout=60
                )
                result = response.json()["result"]
                self.update_status("✅ Manufacturing check complete!", (0, 200, 100))
                wx.MessageBox(result, "Manufacturing Check Result", wx.OK)
            except Exception as e:
                self.update_status("❌ Error!", (255, 50, 50))
                wx.MessageBox(f"Error: {str(e)}\nMake sure FastAPI backend is running!",
                            "Error", wx.OK | wx.ICON_ERROR)
        input_dialog.Destroy()

    def on_drc(self, event):
        input_dialog = wx.TextEntryDialog(
            self,
            "Enter board specifications for DRC:",
            "DRC Check",
            "2 layer board, 0.1mm trace width, 0.2mm clearance"
        )
        if input_dialog.ShowModal() == wx.ID_OK:
            prompt = input_dialog.GetValue()
            self.update_status("⏳ Running DRC...", (255, 200, 0))
            try:
                response = requests.post(
                    "http://127.0.0.1:8000/run_drc",
                    json={"prompt": prompt},
                    timeout=60
                )
                result = response.json()["result"]
                self.update_status("✅ DRC complete!", (0, 200, 100))
                wx.MessageBox(result, "DRC Results", wx.OK)
            except Exception as e:
                self.update_status("❌ Error!", (255, 50, 50))
                wx.MessageBox(f"Error: {str(e)}\nMake sure FastAPI backend is running!",
                            "Error", wx.OK | wx.ICON_ERROR)
        input_dialog.Destroy()


AiKicadPlugin().register()