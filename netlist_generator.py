import pcbnew
import os
from datetime import datetime

def parse_connections_from_ai(ai_response: str):
    components = []
    connections = []
    lines = ai_response.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if 'LED' in line.upper():
            components.append({"ref": "D1", "value": "LED", "lib": "Device", "part": "LED"})
        elif 'RESISTOR' in line.upper() or ' R ' in line.upper():
            components.append({"ref": "R1", "value": "330R", "lib": "Device", "part": "R"})
        elif 'CAPACITOR' in line.upper() or ' C ' in line.upper():
            components.append({"ref": "C1", "value": "100nF", "lib": "Device", "part": "C"})
        elif 'BATTERY' in line.upper() or 'POWER' in line.upper():
            components.append({"ref": "BT1", "value": "9V", "lib": "Device", "part": "Battery"})
        if 'CONNECT' in line.upper() or 'ANODE' in line.upper():
            connections.append(line)
        elif 'CATHODE' in line.upper() or 'GND' in line.upper():
            connections.append(line)

    seen = set()
    unique_components = []
    for c in components:
        if c["ref"] not in seen:
            seen.add(c["ref"])
            unique_components.append(c)

    return unique_components, connections


def generate_netlist_file(components: list, connections: list, output_path: str):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    netlist = f"""(export (version "E")
  (design
    (source "ai_generated")
    (date "{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    (tool "AI KiCad Plugin")
    (sheet (number "1") (name "/") (tstamps "/"))
  )
  (components\n"""

    for i, comp in enumerate(components):
        netlist += f"""    (comp (ref "{comp['ref']}")
      (value "{comp['value']}")
      (libsource (lib "{comp['lib']}") (part "{comp['part']}") (description ""))
      (property (name "Reference") (value "{comp['ref']}"))
      (property (name "Value") (value "{comp['value']}"))
      (sheetpath (names "/") (tstamps "/"))
      (tstamp "{timestamp}{i:04d}")
    )\n"""

    netlist += "  )\n"
    netlist += "  (nets\n"
    
    net_num = 1
    if any(c["ref"] == "D1" for c in components):
        netlist += f"""    (net (code "{net_num}") (name "LED_ANODE")
      (node (ref "D1") (pin "A") (pintype "passive"))
      (node (ref "R1") (pin "1") (pintype "passive"))
    )\n"""
        net_num += 1

    if any(c["ref"] == "R1" for c in components):
        netlist += f"""    (net (code "{net_num}") (name "VCC")
      (node (ref "R1") (pin "2") (pintype "passive"))
      (node (ref "BT1") (pin "1") (pintype "passive"))
    )\n"""
        net_num += 1

    netlist += f"""    (net (code "{net_num}") (name "GND")
      (node (ref "D1") (pin "K") (pintype "passive"))
      (node (ref "BT1") (pin "2") (pintype "passive"))
    )\n"""

    netlist += "  )\n"
    netlist += ")\n"

    with open(output_path, 'w') as f:
        f.write(netlist)

    return output_path


def generate_netlist_from_prompt(ai_response: str, project_path: str = None):
    try:
        components, connections = parse_connections_from_ai(ai_response)

        if not components:
            return "No components found in AI response!"

        if project_path is None:
            board = pcbnew.GetBoard()
            project_path = os.path.dirname(board.GetFileName())

        if not project_path:
            project_path = os.path.expanduser("~\\Documents")

        output_file = os.path.join(project_path, "ai_generated_netlist.net")
        generate_netlist_file(components, connections, output_file)

        return f"✅ Netlist generated!\nComponents: {len(components)}\nSaved to: {output_file}"

    except Exception as e:
        return f"Error generating netlist: {str(e)}"