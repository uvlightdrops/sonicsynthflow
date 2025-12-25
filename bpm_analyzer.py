import pyaudio
import aubio
import numpy as np
import collections

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

    def start(self, on_bpm_callback=None):
        self.callback = on_bpm_callback
        self.inputStream = self.pa.open(format=pyaudio.paFloat32,
                input=True,
                channels=self.channels,
                input_device_index=self.device_index,
                frames_per_buffer=self.buffer_size,
                rate=self.sample_rate,
                stream_callback=self.readAudioFrames)
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
