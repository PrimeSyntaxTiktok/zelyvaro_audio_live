"""Output-only capture and PCM features shared by system and application modes."""
import threading
import time
from collections import deque
import numpy as np
import pyaudiowpatch as pa
from PySide6.QtCore import QThread, Signal
from analysis_audio import AudioAnalyzer


class AudioThread(QThread):
    spectrumReady = Signal(object)
    status = Signal(str)
    issue = Signal(str)

    def __init__(self, parent=None, source=None):
        super().__init__(parent)
        self.frames = 0
        self.peak_rms = 0.0
        self.peak_hz = 0.0
        self.device = ''
        self.sample_rate = 0
        self.error = ''
        self.last_packet = {}
        self.source = source or {'mode': 'system'}

    def publish(self, block, analyzer, actual=True):
        if actual:
            self.frames += len(block)
        packet = analyzer.process(block)
        rms = float(np.sqrt(np.mean(block ** 2)))
        if rms > self.peak_rms:
            self.peak_rms = rms
            self.peak_hz = packet['peakHz']
        self.last_packet = packet
        self.spectrumReady.emit(packet)

    def run(self):
        try:
            if self.source.get('mode') == 'application':
                self.run_application()
            else:
                self.run_system()
        except Exception as exc:
            self.error = f'{type(exc).__name__}: {exc}'
            self.issue.emit(self.error)

    def run_system(self):
        with pa.PyAudio() as audio:
            device = audio.get_default_wasapi_loopback()
            if not device.get('isLoopbackDevice'):
                raise RuntimeError('La sortie choisie ne permet pas le loopback WASAPI.')
            channels = int(device['maxInputChannels'])
            self.sample_rate = int(device['defaultSampleRate'])
            self.device = device['name']
            analyzer = AudioAnalyzer(self.sample_rate)
            chunks = deque(maxlen=12)
            lock = threading.Lock()
            def callback(data, count, timing, flags):
                if data:
                    with lock:
                        chunks.append(data)
                return (None, pa.paContinue)
            with audio.open(format=pa.paFloat32, channels=channels, rate=self.sample_rate,
                            input=True, input_device_index=device['index'], frames_per_buffer=1024,
                            stream_callback=callback) as stream:
                self.status.emit('Windows : ' + self.device)
                last_data = time.monotonic()
                while not self.isInterruptionRequested():
                    with lock:
                        raw = b''.join(chunks)
                        chunks.clear()
                    if raw:
                        block = np.frombuffer(raw, dtype=np.float32).reshape(-1, channels)[-4096:]
                        self.publish(block, analyzer)
                        last_data = time.monotonic()
                    elif time.monotonic() - last_data > .2:
                        self.publish(np.zeros((1024, 2), dtype=np.float32), analyzer, False)
                    if not stream.is_active():
                        raise RuntimeError('La sortie audio a été déconnectée. Relancez la capture.')
                    self.msleep(20)

    def run_application(self):
        from process_audio import ProcessCapture
        self.sample_rate = 48000
        self.device = self.source['name']
        analyzer = AudioAnalyzer(self.sample_rate)
        with ProcessCapture(self.source) as capture:
            self.status.emit('Application : ' + self.device)
            last_data = time.monotonic()
            while not self.isInterruptionRequested():
                block = capture.read()
                if len(block):
                    self.publish(block, analyzer)
                    last_data = time.monotonic()
                elif time.monotonic() - last_data > .2:
                    self.publish(np.zeros((1024, 2), dtype=np.float32), analyzer, False)
                self.msleep(15)

    def stop(self):
        self.requestInterruption()
        return self.wait(12000)
