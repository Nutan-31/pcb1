import pcbnew
import os
import subprocess

FREEROUTING_JAR = "C:\\Users\\B T NUTAN REDDY\\Downloads\\freerouting-2.1.0.jar"

def export_dsn(output_path: str = None):
    """Export PCB as DSN file using KiCad's built-in exporter"""
    try:
        board = pcbnew.GetBoard()

        if output_path is None:
            project_path = os.path.dirname(board.GetFileName())
            if not project_path:
                project_path = os.path.expanduser("~\\Documents")
            output_path = os.path.join(project_path, "board.dsn")

        # Use KiCad's file exporter
        board.Save(board.GetFileName())
        
        # Try different DSN export methods
        try:
            # Method 1
            exporter = pcbnew.ExportSpecctraDSN(board, output_path)
        except:
            try:
                # Method 2
                pcbnew.ExportSpecctraDSN(output_path)
            except:
                try:
                    # Method 3 - use kicad-cli
                    board_file = board.GetFileName()
                    if board_file:
                        result = subprocess.run([
                            "C:\\Program Files\\KiCad\\9.0\\bin\\kicad-cli.exe",
                            "pcb", "export", "specctra",
                            "--output", output_path,
                            board_file
                        ], capture_output=True, text=True, timeout=30)
                        
                        if os.path.exists(output_path):
                            return output_path, f"✅ DSN exported to: {output_path}"
                        else:
                            return None, f"DSN export failed: {result.stderr}"
                    else:
                        return None, "Board file not saved! Please save your PCB first."
                except Exception as e:
                    return None, f"Error: {str(e)}"

        if os.path.exists(output_path):
            return output_path, f"✅ DSN exported to: {output_path}"
        else:
            return None, "DSN file not created!"

    except Exception as e:
        return None, f"Error exporting DSN: {str(e)}"


def import_ses(ses_path: str):
    """Import SES file back to KiCad"""
    try:
        board = pcbnew.GetBoard()

        if not os.path.exists(ses_path):
            return f"SES file not found: {ses_path}"

        try:
            pcbnew.ImportSpecctraSES(board, ses_path)
        except:
            try:
                board_file = board.GetFileName()
                result = subprocess.run([
                    "C:\\Program Files\\KiCad\\9.0\\bin\\kicad-cli.exe",
                    "pcb", "import", "specctra",
                    "--output", board_file,
                    ses_path
                ], capture_output=True, text=True, timeout=30)
            except Exception as e:
                return f"Error importing SES: {str(e)}"

        pcbnew.Refresh()
        return f"✅ Routes imported from: {ses_path}"

    except Exception as e:
        return f"Error importing SES: {str(e)}"


def run_freerouting(dsn_path: str):
    """Run FreeRouting on DSN file"""
    try:
        if not os.path.exists(FREEROUTING_JAR):
            return None, f"FreeRouting JAR not found at: {FREEROUTING_JAR}"

        ses_path = dsn_path.replace(".dsn", ".ses")

        cmd = [
            "C:\\Program Files\\Java\\jdk-21.0.10\\bin\\java.exe", "-jar", FREEROUTING_JAR,
            "-de", dsn_path,
            "-do", ses_path,
            "-mp", "100"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )

        if os.path.exists(ses_path):
            return ses_path, f"✅ FreeRouting completed!"
        else:
            return None, f"FreeRouting failed!\n{result.stdout}\n{result.stderr}"

    except subprocess.TimeoutExpired:
        return None, "FreeRouting timed out!"
    except Exception as e:
        return None, f"Error: {str(e)}"


def auto_route_board():
    """Main function - auto route entire board!"""
    try:
        board = pcbnew.GetBoard()
        footprints = list(board.GetFootprints())

        if not footprints:
            return "No components found on board!"

        # Save board first
        board_file = board.GetFileName()
        if not board_file:
            return "Please save your PCB file first!\nFile → Save"

        board.Save(board_file)

        # Export DSN
        project_path = os.path.dirname(board_file)
        dsn_path = os.path.join(project_path, "board.dsn")

        dsn_path, msg = export_dsn(dsn_path)
        if not dsn_path:
            return f"DSN Export failed!\n{msg}\n\nTry: File → Export → Specctra DSN manually"

        # Run FreeRouting
        ses_path, msg = run_freerouting(dsn_path)
        if not ses_path:
            return f"DSN exported but routing failed!\n{msg}\n\nManually open FreeRouting:\njava -jar freerouting.jar\nThen load: {dsn_path}"

        # Import SES
        result = import_ses(ses_path)
        return f"✅ Auto-routing complete!\n{result}"

    except Exception as e:
        return f"Error: {str(e)}"