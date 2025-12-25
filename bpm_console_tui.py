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
            Layout(name="status", size=6)
        )
        return layout

    def render(self):
        layout = self.make_layout()
        avg_bpm = self.analyzer.get_bpm()
        avg_text = Text(f"\n {avg_bpm:.2f} \n", style="bold green", justify="center")
        avg_panel = Panel(avg_text, title="Moving Average BPM", border_style="green")
        layout["avg_bpm"].update(avg_panel)
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

