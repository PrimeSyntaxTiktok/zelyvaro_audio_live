"""WASAPI output loopback only; microphone access is never requested."""
import threading
import time
from collections import deque

import numpy as np
import pyaudiowpatch as pa
from PySide6.QtCore import QThread, Signal

N = 2048


def spectrum(samples):
    samples = np.asarray(samples, dtype=np.float32)
    if samples.ndim == 1:
        samples = samples[:, None]
    samples = samples[-N:]
    if len(samples) < N:
        samples = np.pad(samples, ((N - len(samples), 0), (0, 0)))
    # Average channel powers, not samples: opposite-phase stereo must not cancel.
    amplitude = np.sqrt(np.mean(np.abs(np.fft.rfft(
        samples * np.hanning(N)[:, None], axis=0)) ** 2, axis=1)) / (N / 4)
    db = 20 * np.log10(np.maximum(amplitude, 1e-8))
    return np.rint(np.clip((db + 70) / 70, 0, 1) * 255).astype(np.uint8).tolist()


class AudioThread(QThread):
    spectrumReady = Signal(list)
    status = Signal(str)
    issue = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.frames = 0
        self.peak_rms = 0.0
        self.peak_hz = 0.0
        self.device = ''
        self.sample_rate = 0
        self.error = ''

    def run(self):
        try:
            # Callback mode keeps shutdown bounded even if the device is silent.
            with pa.PyAudio() as audio:
                device = audio.get_default_wasapi_loopback()
                if not device.get('isLoopbackDevice'):
                    raise RuntimeError('Le périphérique sélectionné ne permet pas le loopback WASAPI.')
                channels = int(device['maxInputChannels'])
                self.sample_rate = int(device['defaultSampleRate'])
                self.device = device['name']
                chunks = deque(maxlen=8)
                lock = threading.Lock()

                def callback(data, count, timing, flags):
                    if data:
                        with lock:
                            chunks.append(data)
                    return (None, pa.paContinue)

                with audio.open(format=pa.paFloat32, channels=channels,
                                rate=self.sample_rate, input=True,
                                input_device_index=device['index'],
                                frames_per_buffer=N, stream_callback=callback) as stream:
                    self.status.emit('● WINDOWS : ' + self.device)
                    last_data = time.monotonic()
                    while not self.isInterruptionRequested():
                        with lock:
                            raw = b''.join(chunks)
                            chunks.clear()
                        if raw:
                            block = np.frombuffer(raw, dtype=np.float32).reshape(-1, channels)[-N:]
                            self.frames += len(block)
                            rms = float(np.sqrt(np.mean(block ** 2)))
                            if rms > self.peak_rms:
                                self.peak_rms = rms
                                powers = np.mean(np.abs(np.fft.rfft(block, axis=0)) ** 2, axis=1)
                                self.peak_hz = float(np.argmax(powers) * self.sample_rate / len(block))
                            self.spectrumReady.emit(spectrum(block))
                            last_data = time.monotonic()
                        elif time.monotonic() - last_data > .25:
                            self.spectrumReady.emit([0] * (N // 2 + 1))
                        if not stream.is_active():
                            raise RuntimeError('La sortie audio a été déconnectée. Relancez la capture après sélection de la sortie Windows.')
                        self.msleep(30)
        except Exception as exc:
            self.error = f'{type(exc).__name__}: {exc}'
            self.issue.emit(self.error)

    def stop(self):
        self.requestInterruption()
        return self.wait(5000)
