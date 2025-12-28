from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
import time
from bpm_analyzer import BPMAnalyzer

from flowpy.utils import setup_logger
logger = setup_logger(__name__, __name__+'.log')

class BPMConsoleGUI:
    def __init__(self, analyzer: BPMAnalyzer, console=None):
        self.analyzer = analyzer
        self.console = console or Console()
        self.start_time = time.time()
        self.status = "Initialisiert"

    def make_layout(self):
        layout = Layout()
        layout.split_column(
            Layout(name="avg_bpm", size=4),
            Layout(name="main", ratio=1),
            Layout(name="status", size=6)
        )
        layout["main"].split_row(
            Layout(name="stable_bpm"),
            Layout(name="outliers")
        )
        return layout

    def render(self):
        layout = self.make_layout()
        avg_bpm = self.analyzer.get_bpm()
        avg_text = Text(f"\n {avg_bpm:.2f} \n", style="bold green", justify="center")
        avg_panel = Panel(avg_text, title="Moving Average BPM", border_style="green")
        layout["avg_bpm"].update(avg_panel)

        # Mapping: Counter-Index -> Wert (entweder stabil oder outlier)
        stable_dict = {i: v for i, v in getattr(self.analyzer, 'single_measurements', []) if (i, v) not in self.analyzer.outliers}
        outlier_dict = {i: v for i, v in self.analyzer.outliers}
        all_indices = sorted(set(list(stable_dict.keys()) + list(outlier_dict.keys())), reverse=True)
        # Begrenzung entfällt, damit die Liste so lang wie der Container werden kann

        # Tabellarische Darstellung: Index | Stabil | Outlier
        lines = []
        for i in all_indices:
            idx_str = f"{i:>4}"
            stable_str = f"{stable_dict[i]:.2f}" if i in stable_dict else ""
            outlier_str = f"{outlier_dict[i]:.2f}" if i in outlier_dict else ""
            lines.append(f"{idx_str} │ {stable_str:>8} │ {outlier_str:>8}")
        header = "Idx │   Stabil  │  Outlier "
        table = "\n".join([header] + lines) if lines else header + "\n-"

        # Panel für beide Spalten gemeinsam
        stable_panel = Panel(table, title="Letzte stabile BPM / Outlier", border_style="cyan")
        layout["stable_bpm"].update(stable_panel)
        layout["outliers"].update(Panel("", border_style="red"))  # Outlier-Panel leer lassen

        elapsed = int(time.time() - self.start_time)
        status_text = f"Gerät: {self.analyzer.audio_device['name']}\nSampleRate: {self.analyzer.sample_rate} \n\n"
        status_text += f"Status: {self.status} seit : {elapsed}s "
        layout["status"].update(Panel(status_text, title="Status", border_style="blue"))
        return layout

    def run(self):
        self.status = "Läuft"
        with Live(self.render(), refresh_per_second=2, screen=True) as live:
            try:
                while self.analyzer.running:
                    live.update(self.render())
                    time.sleep(0.5)
            except KeyboardInterrupt:
                self.status = "Beendet durch Benutzer"
                self.analyzer.stop()
