import pcbnew
import os

def parse_components_from_ai(ai_response: str):
    components = []
    lines = ai_response.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if 'LED' in line.upper():
            components.append({"type": "LED", "reference": "D1", "value": "LED"})
        elif 'RESISTOR' in line.upper() or ' R ' in line.upper():
            components.append({"type": "R", "reference": "R1", "value": "330R"})
        elif 'CAPACITOR' in line.upper() or ' C ' in line.upper():
            components.append({"type": "C", "reference": "C1", "value": "100nF"})
        elif 'BATTERY' in line.upper() or 'POWER' in line.upper():
            components.append({"type": "BT", "reference": "BT1", "value": "9V"})
        elif 'TRANSISTOR' in line.upper():
            components.append({"type": "Q", "reference": "Q1", "value": "NPN"})

    seen = set()
    unique = []
    for c in components:
        if c["type"] not in seen:
            seen.add(c["type"])
            unique.append(c)
    return unique


def add_components_to_pcb(components: list):
    try:
        board = pcbnew.GetBoard()
        x_pos = 50.0
        y_pos = 50.0
        spacing = 25.0
        added = []
        skipped = []

        footprint_map = {
            "LED": ("LED_THT", "LED_D5.0mm"),
            "R": ("Resistor_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),
            "C": ("Capacitor_THT", "C_Disc_D5.0mm_W2.5mm_P5.00mm"),
            "BT": ("Connector_PinHeader_2.54mm", "PinHeader_1x02_P2.54mm_Vertical"),
            "Q": ("Package_TO_SOT_THT", "TO-92_Inline"),
        }

        kicad_path = "C:\\Program Files\\KiCad\\9.0\\share\\kicad\\footprints"

        for i, comp in enumerate(components):
            comp_type = comp["type"]
            if comp_type not in footprint_map:
                skipped.append(comp_type)
                continue

            lib, fp_name = footprint_map[comp_type]

            try:
                # Try with full path first
                lib_path = os.path.join(kicad_path, lib + ".pretty")
                footprint = pcbnew.FootprintLoad(lib_path, fp_name)

                if footprint is None:
                    # Try without path
                    footprint = pcbnew.FootprintLoad(lib, fp_name)

                if footprint is None:
                    skipped.append(comp_type)
                    continue

                footprint.SetReference(comp["reference"])
                footprint.SetValue(comp["value"])
                footprint.SetX(pcbnew.FromMM(x_pos + (i * spacing)))
                footprint.SetY(pcbnew.FromMM(y_pos))
                board.Add(footprint)
                added.append(comp["reference"])

            except Exception as e:
                skipped.append(f"{comp_type}({str(e)[:30]})")
                continue

        pcbnew.Refresh()

        result = ""
        if added:
            result += f"✅ Added: {', '.join(added)}\n"
        if skipped:
            result += f"⚠️ Skipped: {', '.join(skipped)}\n"
        if not added:
            result += "❌ No components added!\n"
        return result

    except Exception as e:
        return f"Error: {str(e)}"


def write_components_from_prompt(ai_response: str):
    components = parse_components_from_ai(ai_response)
    if not components:
        return "No components found in AI response!"
    result = add_components_to_pcb(components)
    return f"Found {len(components)} components.\n{result}"