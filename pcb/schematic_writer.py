import pcbnew
import os
import json
import re

KICAD_FOOTPRINTS_PATH = "C:\\Program Files\\KiCad\\9.0\\share\\kicad\\footprints"

# Footprint mapping for any component type
FOOTPRINT_MAP = {
    # Resistors
    "R": ("Resistor_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),
    "RES": ("Resistor_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),
    
    # Capacitors
    "C": ("Capacitor_THT", "C_Disc_D5.0mm_W2.5mm_P5.00mm"),
    "CAP": ("Capacitor_THT", "C_Disc_D5.0mm_W2.5mm_P5.00mm"),
    
    # LEDs
    "LED": ("LED_THT", "LED_D5.0mm"),
    "D": ("Diode_THT", "D_DO-41_SOD81_P10.16mm_Horizontal"),
    
    # ICs
    "IC": ("Package_DIP", "DIP-8_W7.62mm"),
    "U": ("Package_DIP", "DIP-8_W7.62mm"),
    
    # Transistors
    "Q": ("Package_TO_SOT_THT", "TO-92_Inline"),
    "NPN": ("Package_TO_SOT_THT", "TO-92_Inline"),
    "PNP": ("Package_TO_SOT_THT", "TO-92_Inline"),
    
    # Connectors
    "J": ("Connector_PinHeader_2.54mm", "PinHeader_1x02_P2.54mm_Vertical"),
    "CONN": ("Connector_PinHeader_2.54mm", "PinHeader_1x02_P2.54mm_Vertical"),
    
    # Battery/Power
    "BT": ("Connector_PinHeader_2.54mm", "PinHeader_1x02_P2.54mm_Vertical"),
    "BATTERY": ("Connector_PinHeader_2.54mm", "PinHeader_1x02_P2.54mm_Vertical"),
    
    # Inductors
    "L": ("Inductor_THT", "L_Axial_L5.3mm_D2.2mm_P10.16mm_Horizontal"),
    
    # Switches
    "SW": ("Button_Switch_THT", "SW_PUSH_6mm"),
    "SWITCH": ("Button_Switch_THT", "SW_PUSH_6mm"),
    
    # Crystals
    "Y": ("Crystal", "Crystal_HC49-4H_Vertical"),
    "XTAL": ("Crystal", "Crystal_HC49-4H_Vertical"),
    
    # Potentiometers
    "RV": ("Potentiometer_THT", "Potentiometer_Bourns_3386P_Vertical"),
    "POT": ("Potentiometer_THT", "Potentiometer_Bourns_3386P_Vertical"),
}


def get_footprint(comp_type: str):
    """Get footprint for any component type"""
    comp_type_upper = comp_type.upper()
    
    # Direct match
    if comp_type_upper in FOOTPRINT_MAP:
        return FOOTPRINT_MAP[comp_type_upper]
    
    # Partial match
    for key in FOOTPRINT_MAP:
        if key in comp_type_upper or comp_type_upper in key:
            return FOOTPRINT_MAP[key]
    
    # Default to resistor footprint
    return FOOTPRINT_MAP["R"]


def load_footprint(lib_name: str, fp_name: str):
    """Load footprint from KiCad library"""
    try:
        # Try full path first
        lib_path = os.path.join(KICAD_FOOTPRINTS_PATH, lib_name + ".pretty")
        fp = pcbnew.FootprintLoad(lib_path, fp_name)
        if fp:
            return fp
    except:
        pass
    
    try:
        # Try without path
        fp = pcbnew.FootprintLoad(lib_name, fp_name)
        if fp:
            return fp
    except:
        pass
    
    return None


def _split_ref_pin(value: str):
    if not value:
        return None, None
    text = str(value).strip()
    match = re.match(r'^([A-Za-z]+\d+)[\s:\-_/]*([A-Za-z0-9+\-]+)?$', text)
    if not match:
        return None, None
    return match.group(1).upper(), (match.group(2) or "").upper()


def _normalize_connections(raw_connections):
    normalized = []
    for item in raw_connections or []:
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
            pattern = (
                r'([A-Za-z]+\d+)\s*(?:pin|pad)?\s*([A-Za-z0-9+\-]*)\s*'
                r'(?:to|->|connect(?:ed)?\s*to)\s*'
                r'([A-Za-z]+\d+)\s*(?:pin|pad)?\s*([A-Za-z0-9+\-]*)'
            )
            match = re.search(pattern, item, re.IGNORECASE)
            if match:
                conn = {
                    "from_ref": match.group(1).upper(),
                    "from_pin": (match.group(2) or "").upper(),
                    "to_ref": match.group(3).upper(),
                    "to_pin": (match.group(4) or "").upper(),
                    "net_name": ""
                }

        if conn:
            normalized.append(conn)

    for idx, conn in enumerate(normalized, start=1):
        if not conn.get("net_name"):
            conn["net_name"] = f"NET_{idx}"

    return normalized


def _get_pad_by_pin(footprint, pin: str):
    pads = list(footprint.Pads())
    if not pads:
        return None

    pin_text = (pin or "").strip().upper()
    if not pin_text:
        return pads[0]

    aliases = {
        "A": "1",
        "ANODE": "1",
        "+": "1",
        "VCC": "1",
        "K": "2",
        "CATHODE": "2",
        "-": "2",
        "GND": "2",
    }
    pin_text = aliases.get(pin_text, pin_text)
    if pin_text.startswith("PIN"):
        pin_text = pin_text[3:]

    for pad in pads:
        if str(pad.GetNumber()).upper() == pin_text:
            return pad

    return pads[0]


def _make_unique_net(board, base_name: str):
    net_name = (base_name or "NET").strip().replace(" ", "_")
    net_name = re.sub(r'[^A-Za-z0-9_\-]', '_', net_name)
    if not net_name:
        net_name = "NET"

    index = 0
    while index < 100:
        candidate = net_name if index == 0 else f"{net_name}_{index}"
        try:
            net_item = pcbnew.NETINFO_ITEM(board, candidate)
            board.Add(net_item)
            return net_item
        except Exception:
            index += 1
    return None


def _set_pad_net(pad, net):
    """Set pad net in a KiCad-version-tolerant way."""
    if not pad or not net:
        return

    try:
        if hasattr(pad, "SetNet"):
            pad.SetNet(net)
            return
    except Exception:
        pass

    try:
        if hasattr(pad, "SetNetCode") and hasattr(net, "GetNetCode"):
            pad.SetNetCode(net.GetNetCode())
    except Exception:
        pass


def _connect_components(board, footprint_by_ref: dict, connections: list):
    created = 0
    skipped = 0

    for conn in connections:
        from_fp = footprint_by_ref.get(conn.get("from_ref", "").upper())
        to_fp = footprint_by_ref.get(conn.get("to_ref", "").upper())
        if not from_fp or not to_fp:
            skipped += 1
            continue

        from_pad = _get_pad_by_pin(from_fp, conn.get("from_pin", ""))
        to_pad = _get_pad_by_pin(to_fp, conn.get("to_pin", ""))
        if not from_pad or not to_pad:
            skipped += 1
            continue

        start_pos = from_pad.GetPosition() if from_pad else from_fp.GetPosition()
        end_pos = to_pad.GetPosition() if to_pad else to_fp.GetPosition()

        if start_pos == end_pos:
            skipped += 1
            continue

        try:
            net = _make_unique_net(board, conn.get("net_name", "NET"))
            if net:
                _set_pad_net(from_pad, net)
                _set_pad_net(to_pad, net)

            track = pcbnew.PCB_TRACK(board)
            track.SetLayer(pcbnew.F_Cu)
            track.SetWidth(pcbnew.FromMM(0.30))
            track.SetStart(start_pos)
            track.SetEnd(end_pos)
            if net:
                try:
                    track.SetNet(net)
                except Exception:
                    pass
            board.Add(track)

            created += 1
        except Exception:
            skipped += 1

    return created, skipped


def add_components_from_circuit_data(circuit_data: dict):
    """
    Add components from circuit JSON data to PCB
    Works for ANY circuit type!
    """
    try:
        board = pcbnew.GetBoard()
        components = circuit_data.get("components", [])
        
        if not components:
            return "No components found in circuit data!"
        
        x_pos = 20.0
        y_pos = 50.0
        spacing = 25.0
        
        added = []
        skipped = []
        footprint_by_ref = {}
        
        for i, comp in enumerate(components):
            ref = comp.get("ref", f"U{i+1}")
            comp_type = comp.get("type", "R")
            value = comp.get("value", "")
            
            lib_name, fp_name = get_footprint(comp_type)
            
            try:
                footprint = load_footprint(lib_name, fp_name)
                
                if footprint is None:
                    skipped.append(ref)
                    continue
                
                footprint.SetReference(ref)
                footprint.SetValue(value)
                footprint.SetX(pcbnew.FromMM(x_pos + (i * spacing)))
                footprint.SetY(pcbnew.FromMM(y_pos))
                board.Add(footprint)
                added.append(ref)
                footprint_by_ref[ref.upper()] = footprint
                
            except Exception as e:
                skipped.append(f"{ref}({str(e)[:20]})")
                continue
        
        # Apply connectivity after placement so the board has routable nets/tracks.
        raw_connections = circuit_data.get("connections", [])
        connections = _normalize_connections(raw_connections)

        if not connections and len(added) >= 2:
            for i in range(len(added) - 1):
                connections.append({
                    "from_ref": added[i].upper(),
                    "from_pin": "2",
                    "to_ref": added[i + 1].upper(),
                    "to_pin": "1",
                    "net_name": f"NET_{i + 1}"
                })

        connected, conn_skipped = _connect_components(board, footprint_by_ref, connections)

        try:
            board.BuildConnectivity()
        except Exception:
            pass

        pcbnew.Refresh()
        
        result = ""
        if added:
            result += f"✅ Added: {', '.join(added)}\n"
        if skipped:
            result += f"⚠️ Skipped: {', '.join(skipped)}\n"
        if connected:
            result += f"🔗 Connected nets/tracks: {connected}\n"
        if conn_skipped:
            result += f"⚠️ Unconnected links skipped: {conn_skipped}\n"
        if not added:
            result += "❌ No components added!\n"
        
        return result
        
    except Exception as e:
        return f"Error: {str(e)}"


def parse_components_from_ai(ai_response: str):
    """Parse components from plain text AI response"""
    components = []
    lines = ai_response.split('\n')
    
    component_keywords = {
        'LED': ('LED', 'D', 'LED'),
        'RESISTOR': ('R', 'R', '330R'),
        'CAPACITOR': ('C', 'C', '100nF'),
        'BATTERY': ('BT', 'BT', '9V'),
        'TRANSISTOR': ('Q', 'Q', 'NPN'),
        'IC': ('U', 'U', 'IC'),
        'SWITCH': ('SW', 'SW', 'SW'),
        'INDUCTOR': ('L', 'L', '10uH'),
        'CRYSTAL': ('Y', 'Y', '16MHz'),
        'CONNECTOR': ('J', 'J', 'CONN'),
        'DIODE': ('D', 'D', '1N4007'),
        'MOSFET': ('Q', 'Q', 'MOSFET'),
        'RELAY': ('K', 'J', 'RELAY'),
        'TRANSFORMER': ('T', 'J', 'TRANS'),
        'POTENTIOMETER': ('RV', 'RV', '10K'),
    }
    
    counters = {}
    seen_types = set()
    
    for line in lines:
        line_upper = line.upper()
        for keyword, (ref_prefix, comp_type, default_value) in component_keywords.items():
            if keyword in line_upper and comp_type not in seen_types:
                seen_types.add(comp_type)
                count = counters.get(ref_prefix, 1)
                counters[ref_prefix] = count + 1
                components.append({
                    "ref": f"{ref_prefix}{count}",
                    "type": comp_type,
                    "value": default_value
                })
    
    return components


def write_components_from_prompt(ai_response: str, circuit_data: dict = None):
    """
    Main function — works with both JSON circuit data and plain text
    """
    if circuit_data and circuit_data.get("components"):
        # Use structured JSON data
        result = add_components_from_circuit_data(circuit_data)
        return f"Circuit: {circuit_data.get('circuit_name', 'Unknown')}\nComponents: {len(circuit_data.get('components', []))}\n{result}"
    else:
        # Fall back to text parsing
        components = parse_components_from_ai(ai_response)
        if not components:
            return "No components found!"
        result = add_components_from_circuit_data({"components": components})
        return f"Found {len(components)} components.\n{result}"