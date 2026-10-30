import hashlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from analysis_audio import AudioAnalyzer, N
from updates import parse_release, download_update, Update, trusted_url
from version import REPOSITORY
from process_audio import resolve_source


class SourceTests(unittest.TestCase):
    def test_closed_application_never_becomes_system_audio(self):
        self.assertIsNone(resolve_source({'mode': 'application', 'path': 'C:/Spotify.exe'}, []))

    def test_restart_follows_path_and_rejects_reused_pid(self):
        saved = {'mode': 'application', 'path': 'C:/Spotify.exe', 'pid': 10, 'created': 1}
        foreign = {'mode': 'application', 'path': 'C:/Other.exe', 'pid': 10, 'created': 2}
        restarted = {'mode': 'application', 'path': 'c:/spotify.EXE', 'pid': 20, 'created': 3}
        self.assertIsNone(resolve_source(saved, [foreign]))
        self.assertEqual(resolve_source(saved, [foreign, restarted]), restarted)

    def test_system_mode_stays_system(self):
        self.assertEqual(resolve_source({'mode': 'system'}, [])['mode'], 'system')


class AudioTests(unittest.TestCase):
    def test_silence_is_silence(self):
        packet = AudioAnalyzer().process(np.zeros((N, 2)))
        self.assertEqual(max(packet['bands']), 0)
        self.assertEqual(packet['level'], 0)
        self.assertFalse(packet['signal'])

    def test_stereo_opposite_phase_does_not_cancel(self):
        tone = .1 * np.sin(2 * np.pi * 40 * np.arange(N) / N)
        packet = AudioAnalyzer().process(np.stack((tone, -tone), axis=1))
        self.assertAlmostEqual(packet['peakHz'], 40 * 48000 / N, delta=15)
        self.assertGreater(max(packet['bands']), .8)
        self.assertGreater(max(map(abs, packet['waveform'])), .3)

    def test_bass_and_treble_follow_actual_frequency(self):
        results = []
        for hz in (80, 8000):
            tone = .06 * np.sin(2 * np.pi * hz * np.arange(N) / 48000)
            analyzer = AudioAnalyzer()
            for i in range(8):
                packet = analyzer.process(tone, i * .04)
            results.append(packet)
        self.assertGreater(results[0]['bass'], results[0]['treble'] + .3)
        self.assertGreater(results[1]['treble'], results[1]['bass'] + .3)
        self.assertGreater(int(np.argmax(results[1]['bands'])), int(np.argmax(results[0]['bands'])) + 70)

    def test_pause_clears_real_signal_and_bands(self):
        analyzer = AudioAnalyzer()
        analyzer.process(.08 * np.sin(2 * np.pi * 80 * np.arange(N) / 48000))
        packet = analyzer.process(np.zeros((N, 2)))
        self.assertFalse(packet['signal'])
        self.assertEqual(max(packet['bands']), 0)


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.payload = b'MZ' + bytes(range(255)) * 4
        self.name = 'ZelyvaroAudioLive-99.0.0-setup.exe'
        self.url = f'https://github.com/{REPOSITORY}/releases/download/v99.0.0/{self.name}'
        self.sha = hashlib.sha256(self.payload).hexdigest()
        self.release = {'tag_name': 'v99.0.0', 'assets': [{'name': self.name,
            'browser_download_url': self.url, 'digest': 'sha256:' + self.sha, 'size': len(self.payload)}]}

    def test_stable_newer_only(self):
        self.assertEqual(parse_release(self.release).version, '99.0.0')
        self.assertIsNone(parse_release(self.release, '99.0.0'))
        for changes in ({'draft': True}, {'prerelease': True}, {'tag_name': 'v2.0.0rc1'}, {'tag_name': 'bad'}):
            self.assertIsNone(parse_release({**self.release, **changes}))

    def test_untrusted_urls_rejected(self):
        for url in ('http://github.com/a', 'https://evil.test/a',
                    'https://github.com.evil.test/a', 'https://user@github.com/a',
                    'https://github.com/other/repo/releases/download/v1/setup.exe'):
            self.assertFalse(trusted_url(url))

    def test_missing_digest_rejected(self):
        self.release['assets'][0]['digest'] = None
        with self.assertRaises(ValueError):
            parse_release(self.release)

    def test_download_verified_and_progress(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch('updates.open_url', return_value=io.BytesIO(self.payload)):
                progress = []
                result = download_update(parse_release(self.release), directory, progress.append)
            self.assertEqual(result.read_bytes(), self.payload)
            self.assertEqual(progress[-1], 100)

    def test_corruption_and_truncation_never_produce_executable(self):
        for payload in (self.payload[:-1], b'MZ' + b'X' * (len(self.payload) - 2)):
            with tempfile.TemporaryDirectory() as directory:
                with patch('updates.open_url', return_value=io.BytesIO(payload)):
                    with self.assertRaises(ValueError):
                        download_update(parse_release(self.release), directory)
                self.assertEqual(list(Path(directory).rglob('*.exe')), [])


if __name__ == '__main__':
    unittest.main()
