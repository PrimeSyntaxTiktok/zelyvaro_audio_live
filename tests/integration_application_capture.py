"""Opt-in real hardware test: selected child-process audio versus another app."""
from pathlib import Path
import json
import subprocess
import sys
import time
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
from process_audio import applications, ProcessCapture, resolve_source


def test(report_path):
    player = ROOT / 'build/native/tone_player.exe'
    started = time.monotonic()
    target = subprocess.Popen([str(player), '523.25', '10', '3', '6', 'tree'], creationflags=subprocess.CREATE_NO_WINDOW)
    other = subprocess.Popen([str(player), '1480', '10', '20', '21'], creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        source = None
        for _ in range(40):
            apps = applications()
            source = next((item for item in apps if item['pid'] == target.pid), None)
            second = next((item for item in apps if item['pid'] == other.pid), None)
            if source and second:
                break
            time.sleep(.05)
        assert source and second, 'Playback apps not enumerated (including child-process grouping)'
        blocks = []
        excluded_live_rms = 0.0
        with ProcessCapture(source) as capture, ProcessCapture(second) as excluded:
            while time.monotonic() - started < 8:
                block = capture.read()
                elapsed = time.monotonic() - started
                if len(block):
                    blocks.append((elapsed, block))
                if 4 < elapsed < 5:
                    extra = excluded.read(10)
                    if len(extra):
                        excluded_live_rms = max(excluded_live_rms, float(np.sqrt(np.mean(extra ** 2))))
        on = np.concatenate([block for t, block in blocks if .7 < t < 2.7])
        quiet = np.concatenate([block for t, block in blocks if 3.6 < t < 5.5])
        resumed = np.concatenate([block for t, block in blocks if 6.6 < t < 7.8])
        on_rms = float(np.sqrt(np.mean(on ** 2)))
        quiet_rms = float(np.sqrt(np.mean(quiet ** 2)))
        resumed_rms = float(np.sqrt(np.mean(resumed ** 2)))
        mono = on.mean(axis=1)
        powers = np.abs(np.fft.rfft(mono * np.hanning(len(mono)))) ** 2
        hz = np.fft.rfftfreq(len(mono), 1 / 48000)
        selected_power = float(powers[np.abs(hz - 523.25) < 8].sum())
        other_power = float(powers[np.abs(hz - 1480) < 8].sum())
        separation_db = float(10 * np.log10(max(selected_power, 1e-20) / max(other_power, 1e-20)))
        report = {'selected_pid': target.pid, 'excluded_pid': other.pid,
                  'child_process_grouped': source['pid'] == target.pid,
                  'selected_hz': 523.25, 'excluded_hz': 1480,
                  'selected_rms': on_rms, 'paused_selected_rms': quiet_rms,
                  'resumed_selected_rms': resumed_rms, 'excluded_app_still_playing_rms': excluded_live_rms,
                  'separation_db': separation_db,
                  'passed': bool(on_rms > .001 and resumed_rms > .001 and excluded_live_rms > .001
                                 and quiet_rms < on_rms * .01 and separation_db > 40)}
        Path(report_path).write_text(json.dumps(report, indent=2), encoding='utf8')
        print(json.dumps(report, indent=2))
        assert report['passed'], 'Application audio isolation failed'
    finally:
        # Both helpers have a fixed ten-second lifetime; allow normal child cleanup.
        target.wait(timeout=12)
        other.wait(timeout=12)


if __name__ == '__main__':
    test(sys.argv[1])
