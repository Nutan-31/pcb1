import pcbnew

class ManufacturingChecks:
    def __init__(self):
        self.board = pcbnew.GetBoard()
        self.issues = []

    def run_all_checks(self):
        """Run all manufacturing checks"""
        self.issues = []
        self.check_trace_width()
        self.check_clearance()
        self.check_drill_sizes()
        self.check_board_edges()
        self.check_silkscreen()
        return self.issues

    def check_trace_width(self):
        """Check if trace widths meet minimum requirements"""
        MIN_TRACE_WIDTH = 0.1  # mm
        for track in self.board.GetTracks():
            width = pcbnew.ToMM(track.GetWidth())
            if width < MIN_TRACE_WIDTH:
                self.issues.append({
                    "type": "Trace Width",
                    "severity": "ERROR",
                    "message": f"Trace width {width:.3f}mm is below minimum {MIN_TRACE_WIDTH}mm"
                })

    def check_clearance(self):
        """Check spacing between components"""
        MIN_CLEARANCE = 0.2  # mm
        tracks = list(self.board.GetTracks())
        for i in range(len(tracks)):
            for j in range(i + 1, len(tracks)):
                dist = pcbnew.ToMM(
                    tracks[i].GetX() - tracks[j].GetX()
                )
                if abs(dist) < MIN_CLEARANCE:
                    self.issues.append({
                        "type": "Clearance",
                        "severity": "WARNING",
                        "message": f"Clearance {abs(dist):.3f}mm is below minimum {MIN_CLEARANCE}mm"
                    })

    def check_drill_sizes(self):
        """Check if drill sizes are manufacturable"""
        MIN_DRILL_SIZE = 0.2  # mm
        for footprint in self.board.GetFootprints():
            for pad in footprint.Pads():
                drill = pcbnew.ToMM(pad.GetDrillSize().x)
                if drill > 0 and drill < MIN_DRILL_SIZE:
                    self.issues.append({
                        "type": "Drill Size",
                        "severity": "ERROR",
                        "message": f"Drill size {drill:.3f}mm is below minimum {MIN_DRILL_SIZE}mm"
                    })

    def check_board_edges(self):
        """Check if board outline is properly defined"""
        edge_cuts = [
            drawing for drawing in self.board.GetDrawings()
            if drawing.GetLayer() == pcbnew.Edge_Cuts
        ]
        if len(edge_cuts) == 0:
            self.issues.append({
                "type": "Board Edge",
                "severity": "ERROR",
                "message": "No board outline found on Edge.Cuts layer!"
            })

    def check_silkscreen(self):
        """Check silkscreen for overlapping text"""
        footprints = list(self.board.GetFootprints())
        for i in range(len(footprints)):
            for j in range(i + 1, len(footprints)):
                dist = pcbnew.ToMM(
                    abs(footprints[i].GetX() - footprints[j].GetX())
                )
                if dist < 1.0:
                    self.issues.append({
                        "type": "Silkscreen",
                        "severity": "WARNING",
                        "message": f"Possible silkscreen overlap between {footprints[i].GetReference()} and {footprints[j].GetReference()}"
                    })

    def generate_report(self):
        """Generate a readable report of all issues"""
        issues = self.run_all_checks()

        if not issues:
            return "✅ No manufacturing issues found!"

        report = f"Manufacturing Check Report\n"
        report += f"{'='*40}\n"
        report += f"Total Issues Found: {len(issues)}\n\n"

        errors = [i for i in issues if i['severity'] == 'ERROR']
        warnings = [i for i in issues if i['severity'] == 'WARNING']

        if errors:
            report += f"❌ ERRORS ({len(errors)}):\n"
            for err in errors:
                report += f"  [{err['type']}] {err['message']}\n"

        if warnings:
            report += f"\n⚠️ WARNINGS ({len(warnings)}):\n"
            for warn in warnings:
                report += f"  [{warn['type']}] {warn['message']}\n"

        return report