import pcbnew
import os
from datetime import datetime

def export_gerbers(output_dir: str = None):
    try:
        board = pcbnew.GetBoard()
        
        if output_dir is None:
            project_path = os.path.dirname(board.GetFileName())
            if not project_path:
                project_path = os.path.expanduser("~\\Documents")
            output_dir = os.path.join(project_path, "gerbers")

        os.makedirs(output_dir, exist_ok=True)

        plot_controller = pcbnew.PLOT_CONTROLLER(board)
        plot_options = plot_controller.GetPlotOptions()

        plot_options.SetOutputDirectory(output_dir)
        plot_options.SetPlotFrameRef(False)
        plot_options.SetPlotValue(True)
        plot_options.SetPlotReference(True)
        plot_options.SetSketchPadsOnFabLayers(False)
        plot_options.SetSubtractMaskFromSilk(True)
        plot_options.SetFormat(pcbnew.PLOT_FORMAT_GERBER)
        plot_options.SetGerberPrecision(6)
        plot_options.SetUseGerberX2format(True)
        plot_options.SetIncludeGerberNetlistInfo(True)

        layers = [
            (pcbnew.F_Cu, "F_Cu", "Front Copper"),
            (pcbnew.B_Cu, "B_Cu", "Back Copper"),
            (pcbnew.F_Paste, "F_Paste", "Front Paste"),
            (pcbnew.B_Paste, "B_Paste", "Back Paste"),
            (pcbnew.F_SilkS, "F_SilkS", "Front Silkscreen"),
            (pcbnew.B_SilkS, "B_SilkS", "Back Silkscreen"),
            (pcbnew.F_Mask, "F_Mask", "Front Mask"),
            (pcbnew.B_Mask, "B_Mask", "Back Mask"),
            (pcbnew.Edge_Cuts, "Edge_Cuts", "Board Outline"),
        ]

        exported = []
        for layer_id, layer_name, layer_desc in layers:
            try:
                plot_controller.SetLayer(layer_id)
                plot_controller.OpenPlotfile(
                    layer_name,
                    pcbnew.PLOT_FORMAT_GERBER,
                    layer_desc
                )
                plot_controller.PlotLayer()
                plot_controller.ClosePlot()
                exported.append(layer_name)
            except Exception as e:
                print(f"Could not export {layer_name}: {str(e)}")
                continue

        try:
            drill_writer = pcbnew.EXCELLON_WRITER(board)
            drill_writer.SetOptions(
                False,
                True,
                pcbnew.VECTOR2I(0, 0),
                True
            )
            drill_writer.SetFormat(True)
            drill_writer.CreateDrillandMapFilesSet(output_dir, True, False)
            exported.append("Drill files")
        except Exception as e:
            print(f"Could not export drill files: {str(e)}")

        try:
            bom_file = os.path.join(output_dir, "BOM.csv")
            with open(bom_file, 'w') as f:
                f.write("Reference,Value,Footprint\n")
                for footprint in board.GetFootprints():
                    f.write(f"{footprint.GetReference()},{footprint.GetValue()},{footprint.GetFPIDAsString()}\n")
            exported.append("BOM.csv")
        except Exception as e:
            print(f"Could not export BOM: {str(e)}")

        return f"✅ Exported {len(exported)} files!\nSaved to: {output_dir}\nFiles: {', '.join(exported)}"

    except Exception as e:
        return f"Error exporting Gerbers: {str(e)}"