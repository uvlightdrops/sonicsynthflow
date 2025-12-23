import pyaudio
import aubio
import numpy as np
import collections
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout

import time
import csv
import os
from datetime import datetime
from rich.text import Text
from rich import box

class BPMMonitorApp:
    def __init__(self, device_index=4, channels=1, buffer_size=512, window_mult=4, window_size=5):
        self.device_index = device_index
        self.channels = channels
        self.buffer_size = buffer_size
        self.window_mult = window_mult
        self.window_size = window_size
        self.bpm_values = collections.deque(maxlen=window_size)
        self.num_outliers = 8  # Anzahl der aufeinanderfolgenden Ausreißer für Trendübernahme
        self.outliers = []
        self.accepted_outliers = []  # Für ausgegraute Ausreißer nach Trendübernahme
        self.threshold_default = 4.0  # Z-Score Schwellenwert für Ausreißererkennung
        self.single_measurements = []
        self.console = Console()
        self.pa = pyaudio.PyAudio()
        self.audio_device = self.pa.get_device_info_by_index(device_index)
        self.sample_rate = int(self.audio_device['defaultSampleRate'])
        self.tempoDetection = aubio.tempo(method='default', buf_size=buffer_size*window_mult, hop_size=buffer_size, samplerate=self.sample_rate)
        self.start_time = time.time()
        self.status = "Initialisiert"
        self.consecutive_outliers = 0  # Zähler für aufeinanderfolgende Ausreißer
        self.measurement_counter = 0  # globaler Index für alle Messungen

    def is_outlier(self, value, values, threshold=4.0):
        if len(values) < 2:
            return False
        mean = np.mean(values)
        std = np.std(values)
        if std == 0:
            return False
        z_score = abs((value - mean) / std)
        return z_score > threshold

    def log_trend_adoption(self, prev_avg, new_value, outlier_value):
        now = datetime.now()
        csv_dir = os.path.join(os.getcwd(), "csv")
        os.makedirs(csv_dir, exist_ok=True)
        filename = now.strftime("trend_adoptions_%Y%m%d_%H.csv")
        filepath = os.path.join(csv_dir, filename)
        file_exists = os.path.isfile(filepath)
        with open(filepath, mode='a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                writer.writerow(["timestamp", "prev_avg_bpm", "adopted_bpm", "outlier_bpm"])
            writer.writerow([
                now.strftime("%Y-%m-%d %H:%M:%S"),
                f"{prev_avg:.2f}",
                f"{new_value:.2f}",
                f"{outlier_value:.2f}"
            ])

    def readAudioFrames(self, in_data, frame_count, time_info, status):
        signal = np.frombuffer(in_data, dtype=np.float32)
        beat = self.tempoDetection(signal)
        if beat:
            bpm = self.tempoDetection.get_bpm()
            self.measurement_counter += 1
            # Fallback: Wenn weniger als 3 valide Werte, akzeptiere alles als valide
            if len(self.bpm_values) < 3:
                self.bpm_values.append(bpm)
                self.single_measurements.append((self.measurement_counter, bpm))
                self.consecutive_outliers = 0
            elif not self.is_outlier(bpm, list(self.bpm_values), threshold=self.threshold_default):
                self.bpm_values.append(bpm)
                self.single_measurements.append((self.measurement_counter, bpm))
                self.consecutive_outliers = 0
            else:
                self.outliers.append((self.measurement_counter, bpm))
                self.consecutive_outliers += 1
                # Wenn x Ausreißer in Folge, akzeptiere den nächsten Wert als neuen Startpunkt
                if self.consecutive_outliers >= self.num_outliers:
                    prev_avg = np.mean(self.bpm_values) if self.bpm_values else 0.0
                    # Die letzten 5 Ausreißer als akzeptiert markieren und loggen
                    for idx, outlier in self.outliers[-self.num_outliers:]:
                        self.log_trend_adoption(prev_avg, bpm, outlier)
                    self.accepted_outliers.extend(self.outliers[-self.num_outliers:])
                    self.bpm_values.clear()
                    self.bpm_values.append(bpm)
                    self.single_measurements.append((self.measurement_counter, bpm))
                    self.outliers = []
                    self.consecutive_outliers = 0

        return (in_data, pyaudio.paContinue)

    def make_layout(self):
        layout = Layout()
        # Oberste Zeile: Moving Average (volle Breite)
        layout.split_column(
            Layout(name="avg_bpm", size=4),
            Layout(name="tables", ratio=3),
            Layout(name="status", size=6)
        )
        # Mittlerer Bereich: Nur eine zentrale Tabelle
        # Kein split_row mehr, sondern ein einziges Feld für die Messungstabelle
        return layout

    def render(self):
        layout = self.make_layout()

        # --- Moving Average Panel ---
        avg_bpm = np.mean(self.bpm_values) if self.bpm_values else 0.0
        avg_text = Text(f"\n {avg_bpm:.2f} \n", style="bold green", justify="center")
        avg_panel = Panel(avg_text, title="Moving Average BPM", border_style="green")
        layout["avg_bpm"].update(avg_panel)

        # --- Dynamische Zeilenzahl je nach Terminalhöhe ---
        term_height = self.console.size.height if hasattr(self.console, 'size') else 24
        # Abzug: 4 für avg_bpm, 6 für status, 6 für Panel-Ränder und Titel, 1 für Rahmenkorrektur
        max_rows = max(5, term_height - 4 - 6 - 6 - 1)

        # --- Indizes der letzten Messungen bestimmen ---
        last_indices = sorted(set(
            [idx for idx, _ in self.single_measurements[-2*max_rows:]] +
            [idx for idx, _ in self.accepted_outliers[-2*max_rows:]] +
            [idx for idx, _ in self.outliers[-2*max_rows:]]
        ))[-max_rows:]

        # --- Tabelle vorbereiten ---
        table = Table(title="Messungen", show_header=True, header_style="bold magenta", box=box.SQUARE, padding=(0,2), min_width=32)
        table.add_column("#", justify="right", min_width=4, max_width=6, no_wrap=True)
        table.add_column("BPM", justify="right", min_width=10, max_width=10, no_wrap=True)
        table.add_column("Ausreißer", justify="right", min_width=10, max_width=10, no_wrap=True)

        # --- Mapping für schnellen Zugriff ---
        valid_map = dict(self.single_measurements)
        outlier_map = dict(self.accepted_outliers + self.outliers)

        # --- Zeilen zur Tabelle hinzufügen ---
        for idx in last_indices:
            if idx in valid_map:
                table.add_row(str(idx), f"{valid_map[idx]:.2f}", "")
            elif idx in outlier_map:
                style = "grey30" if (idx, outlier_map[idx]) in self.accepted_outliers else None
                table.add_row(str(idx), "", f"{outlier_map[idx]:.2f}", style=style)
            else:
                table.add_row(str(idx), "", "")

        # --- Tabelle mittig im Panel mit rotem Rahmen ---
        layout["tables"].update(Panel(table, border_style="red", padding=(1,2)))

        # --- Status Panel (volle Breite unten) ---
        elapsed = int(time.time() - self.start_time)
        status_text = f"Gerät: {self.audio_device['name']}\nSampleRate: {self.sample_rate} \n\n"
        status_text += f"Status: {self.status} seit : {elapsed}s "
        layout["status"].update(Panel(status_text, title="Status", border_style="blue"))

        return layout


    def run(self):
        inputStream = self.pa.open(format=pyaudio.paFloat32,
                input=True,
                channels=self.channels,
                input_device_index=self.device_index,
                frames_per_buffer=self.buffer_size,
                rate=self.sample_rate,
                stream_callback=self.readAudioFrames)
        self.status = "Läuft"

        with Live(self.render(), refresh_per_second=2, screen=True) as live:
            try:
                while True:
                    live.update(self.render())
                    time.sleep(0.5)
            except KeyboardInterrupt:
                self.status = "Beendet durch Benutzer"
                inputStream.stop_stream()
                inputStream.close()
                self.pa.terminate()

if __name__ == "__main__":
    app = BPMMonitorApp()
    app.run()
