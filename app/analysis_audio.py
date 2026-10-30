"""PCM-driven logarithmic spectrum, waveform, level and transient analysis."""
import time
import numpy as np

N = 4096
BANDS = 128


class AudioAnalyzer:
    def __init__(self, sample_rate=48000):
        self.rate = sample_rate
        self.buffer = np.empty((0, 2), dtype=np.float32)
        self.window = np.hanning(N).astype(np.float32)
        self.frequencies = np.fft.rfftfreq(N, 1 / sample_rate)
        edges = np.geomspace(30, min(18000, sample_rate * .46), BANDS + 1)
        self.ranges = []
        for low, high in zip(edges[:-1], edges[1:]):
            a = max(1, int(np.searchsorted(self.frequencies, low)))
            b = max(a + 1, int(np.searchsorted(self.frequencies, high)))
            self.ranges.append((min(a, N // 2), min(b, N // 2 + 1)))
        self.gain_db = 12.0
        self.previous = np.zeros(BANDS)
        self.flux_mean = .015
        self.rms_mean = .01
        self.last_beat = -100.0
        self.beat_id = 0

    def process(self, samples, now=None):
        now = time.monotonic() if now is None else now
        block = np.nan_to_num(np.asarray(samples, dtype=np.float32), nan=0, posinf=0, neginf=0)
        if block.ndim == 1:
            block = block[:, None]
        if block.shape[1] == 1:
            block = np.repeat(block, 2, axis=1)
        if block.shape[1] > 2:
            # Preserve channel power in a stereo representation for multichannel outputs.
            powers = np.mean(block ** 2, axis=0)
            block = block[:, np.argsort(powers)[-2:]]
        if not len(block):
            block = np.zeros((1024, 2), dtype=np.float32)
        rms = float(np.sqrt(np.mean(block ** 2)))
        db = float(20 * np.log10(max(rms, 1e-7)))
        signal = db > -75
        if signal:
            wanted = float(np.clip(-17 - db, 0, 28))
            self.gain_db += (wanted - self.gain_db) * (.1 if wanted < self.gain_db else .025)
        gain = 10 ** (self.gain_db / 20)
        self.buffer = np.concatenate((self.buffer, block))[-N:]
        padded = np.pad(self.buffer, ((N - len(self.buffer), 0), (0, 0)))
        transformed = np.fft.rfft(padded * self.window[:, None], axis=0)
        amplitude = np.sqrt(np.mean(np.abs(transformed) ** 2, axis=1)) / (N / 4)
        # Peak amplitude within each real logarithmic frequency band.
        magnitudes = np.array([np.max(amplitude[a:b]) for a, b in self.ranges])
        levels = 20 * np.log10(np.maximum(magnitudes, 1e-8)) + self.gain_db
        bands = np.clip((levels + 62) / 54, 0, 1) ** 1.35
        if not signal:
            bands[:] = 0
        flux = float(np.mean(np.maximum(0, bands - self.previous)))
        onset = signal and now - self.last_beat > .18 and (
            flux > max(.018, self.flux_mean * 1.65) or rms > max(.001, self.rms_mean * 1.55))
        if onset:
            self.beat_id += 1
            self.last_beat = now
        self.previous = bands
        self.flux_mean = .94 * self.flux_mean + .06 * flux
        self.rms_mean = .94 * self.rms_mean + .06 * rms
        channels = np.mean(padded[-2048:] ** 2, axis=0)
        mono = padded[-2048:, int(np.argmax(channels))]
        crossings = np.flatnonzero((mono[:-1] <= 0) & (mono[1:] > 0))
        crossings = crossings[crossings < 700]
        if len(crossings):
            start = int(crossings[np.argmin(np.abs(crossings - 256))])
            mono = mono[start:start + 1024]
        waveform = np.interp(np.linspace(0, len(mono) - 1, 256), np.arange(len(mono)), mono)
        waveform = np.clip(waveform * gain * 2.4, -1, 1) if signal else np.zeros(256)
        power = amplitude ** 2
        def energy(low, high):
            value = float(np.sqrt(np.sum(power[(self.frequencies >= low) & (self.frequencies < high)])))
            return float(np.clip(np.sqrt(max(0, value * gain * 3)), 0, 1)) if signal else 0.0
        return {'bands': np.round(bands, 4).tolist(), 'waveform': np.round(waveform, 4).tolist(),
                'level': float(np.clip(np.sqrt(rms * gain * 3), 0, 1)) if signal else 0.0,
                'bass': energy(30, 180), 'mid': energy(180, 2500), 'treble': energy(2500, 18000),
                'rmsDb': round(db, 2), 'signal': signal,
                'beat': 1.0 if onset else 0.0, 'beatId': self.beat_id,
                'sampleRate': self.rate, 'peakHz': float(self.frequencies[int(np.argmax(amplitude))]),
                'gainDb': round(self.gain_db, 2)}
