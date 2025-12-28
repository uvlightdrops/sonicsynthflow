import pyaudio
import aubio
import numpy as np
import collections
import time
from flowpy.utils import setup_logger
logger = setup_logger(__name__, __name__+'.log')


class BPMAnalyzer:
    def __init__(self, device_index=4, channels=1, buffer_size=512, window_mult=4, window_size=5):
        self.device_index = device_index
        self.channels = channels
        self.buffer_size = buffer_size
        self.window_mult = window_mult
        self.window_size = window_size
        self.pa = pyaudio.PyAudio()
        self.audio_device = self.pa.get_device_info_by_index(device_index)
        self.sample_rate = int(self.audio_device['defaultSampleRate'])
        self.tempoDetection = aubio.tempo(method='default', buf_size=buffer_size*window_mult, hop_size=buffer_size, samplerate=self.sample_rate)
        self.bpm_values = collections.deque(maxlen=window_size)
        self.last_bpm = None
        self.inputStream = None
        self.running = False
        self.callback = None  # Callback für BPM-Änderung
        # ORIG logic
        self.num_outliers = 12  # Anzahl der aufeinanderfolgenden Ausreißer für Trendübernahme
        self.outliers = []
        self.accepted_outliers = []  # Für ausgegraute Ausreißer nach Trendübernahme
        self.threshold_default = 4.0  # Z-Score Schwellenwert für Ausreißererkennung
        self.single_measurements = []
        self.start_time = time.time()
        self.status = "Initialisiert"
        self.num_consec_outliers = 0  # Zähler für aufeinanderfolgende Ausreißer
        self.counter = 0  # globaler Index für alle Messungen

    def start(self, on_bpm_callback=None):
        self.callback = on_bpm_callback
        self.inputStream = self.pa.open(format=pyaudio.paFloat32,
                input=True,
                channels=self.channels,
                input_device_index=self.device_index,
                frames_per_buffer=self.buffer_size,
                rate=self.sample_rate,
                stream_callback=self.readAudioFrames_ORIG)
                #stream_callback = self.readAudioFrames)
        self.running = True
        self.inputStream.start_stream()

    def stop(self):
        if self.inputStream:
            self.inputStream.stop_stream()
            self.inputStream.close()
        self.pa.terminate()
        self.running = False

    def readAudioFrames(self, in_data, frame_count, time_info, status):
        signal = np.frombuffer(in_data, dtype=np.float32)
        beat = self.tempoDetection(signal)
        if beat:
            bpm = self.tempoDetection.get_bpm()
            if bpm > 0:
                prev_bpm = self.last_bpm
                self.last_bpm = bpm
                self.bpm_values.append(bpm)
                if self.callback and (prev_bpm is None or abs(prev_bpm - bpm) > 0.1):
                    bpm_n = round(bpm, 2)
                    prev_bpm_n = round(prev_bpm, 2) if prev_bpm is not None else None
                    self.callback(bpm_n, prev_bpm_n)
        return (in_data, pyaudio.paContinue)

    def get_bpm(self):
        if self.bpm_values:
            return np.mean(self.bpm_values)
        return 0.0

    def is_outlier(self, value, values, threshold=4.0):
        if len(values) < 2:
            return False
        mean = np.mean(values)
        std = np.std(values)
        if std == 0:
            return False
        z_score = abs((value - mean) / std)
        return z_score > threshold

    def filter_outliers(self, values, threshold=None):
        # Filtert Ausreißer aus einer Liste von (idx, bpm)-Tupeln basierend auf Z-Score
        if threshold is None:
            threshold = self.threshold_default
        if len(values) < 2:
            return [v for _, v in values]
        bpms = [v for _, v in values]
        mean = np.mean(bpms)
        std = np.std(bpms)
        if std == 0:
            return bpms
        filtered = [v for v in bpms if abs((v - mean) / std) <= threshold]
        return filtered

    def readAudioFrames_ORIG(self, in_data, frame_count, time_info, status):
        signal = np.frombuffer(in_data, dtype=np.float32)
        beat = self.tempoDetection(signal)
        if beat:
            bpm = self.tempoDetection.get_bpm()
            print(round(bpm, 2))
            self.counter += 1
            # Fallback: Wenn weniger als 3 valide Werte, akzeptiere alles als valide
            if len(self.bpm_values) < 3:
                self.bpm_values.append(bpm)
                self.single_measurements.append((self.counter, bpm))
                self.num_consec_outliers = 0
            elif not self.is_outlier(bpm, list(self.bpm_values), threshold=self.threshold_default):
                self.bpm_values.append(bpm)
                self.single_measurements.append((self.counter, bpm))
                self.num_consec_outliers = 0
            else:
                self.outliers.append((self.counter, bpm))
                self.num_consec_outliers += 1
                # Wenn x Ausreißer in Folge, prüfe die letzten Outlier intern auf Ausreißer
                if self.num_consec_outliers >= self.num_outliers:
                    prev_avg = np.mean(self.bpm_values) if self.bpm_values else 0.0
                    self.accepted_outliers.extend(self.outliers[-self.num_outliers:])
                    # Filtere die letzten num_outliers Outlier intern
                    last_outliers = self.outliers[-self.num_outliers:]
                    filtered_bpm = self.filter_outliers(last_outliers)
                    print(filtered_bpm)
                    self.bpm_values.clear()
                    # Übernehme nur die gefilterten Werte
                    for v in filtered_bpm:
                        self.bpm_values.append(v)
                    print(self.bpm_values)
                    self.bpm_values.append(bpm)  # aktuellen Wert immer übernehmen
                    self.single_measurements.append((self.counter, bpm))
                    self.outliers = []
                    self.num_consec_outliers = 0
                    # Notify callback sends the new BPM over network
                    if self.callback:
                        avg_bpm = np.mean(self.bpm_values) if self.bpm_values else 0.0
                        bpm_n = round(avg_bpm, 2)
                        self.callback(bpm_n, bpm_n)

        return (in_data, pyaudio.paContinue)
