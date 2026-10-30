"""Opt-in diagnostic mode shared by source and frozen executable."""
import io
import json
import math
import struct
import wave
import winsound
import hashlib

from PySide6.QtCore import QTimer
from version import VERSION


def run_probe(app, window, args):
    report = {'version': VERSION, 'web_loaded': False, 'javascript_bridge': False}
    args.self_test.parent.mkdir(parents=True, exist_ok=True)
    report['themes'] = {}
    if args.gallery:
        def select(theme):
            window.web.page().runJavaScript("window.setTheme('" + theme + "');if(!document.body.classList.contains('clean'))window.toggleClean()")

        def capture(theme):
            path = args.self_test.with_name(args.self_test.stem + '-' + theme + '.png')
            window.grab().save(str(path))
            report['themes'][theme] = hashlib.sha256(path.read_bytes()).hexdigest()

        for i, theme in enumerate(('galaxy', 'city', 'ember', 'aurora', 'abyss', 'gold')):
            QTimer.singleShot(2000 + i * 1400, lambda theme=theme: select(theme))
            QTimer.singleShot(3000 + i * 1400, lambda theme=theme: capture(theme))
        QTimer.singleShot(11000, lambda: window.web.page().runJavaScript("window.setTheme('galaxy');window.toggleClean();document.getElementById('settings').classList.add('open')"))
        QTimer.singleShot(12000, lambda: window.grab().save(str(args.self_test.with_name(args.self_test.stem + '-settings.png'))))
        QTimer.singleShot(12500, lambda: window.web.page().runJavaScript("document.getElementById('settings').classList.remove('open')"))
    if args.play_test_tone:
        output = io.BytesIO()
        with wave.open(output, 'wb') as wav:
            wav.setparams((2, 2, 48000, 0, 'NONE', 'not compressed'))
            samples = b''.join(struct.pack('<hh', value, value) for value in (
                int(2400 * math.sin(2 * math.pi * 1000 * i / 48000)) for i in range(48000 * 4)))
            wav.writeframes(samples)
        tone = output.getvalue()
        import threading
        QTimer.singleShot(1500, lambda: threading.Thread(
            target=lambda: winsound.PlaySound(tone, winsound.SND_MEMORY), daemon=True).start())

    def finish():
        report['web_loaded'] = window.ready
        audio = window.audio
        report.update(device=audio.device, captured_frames=audio.frames,
                      sample_rate=audio.sample_rate, peak_rms=audio.peak_rms,
                      peak_hz=audio.peak_hz, audio_error=audio.error)
        script = "JSON.stringify({bridge:!!window.desktopBridge,active:window.desktopAudioActive,frames:window.desktopFrameCount,animation_frames:window.sceneEngine.frameCount,animation_time:window.sceneEngine.time,canvas:document.getElementById('visual').width,errors:window.jsErrors||[]})"

        def result(value):
            report['renderer'] = json.loads(value) if value else {}
            report['javascript_bridge'] = report['renderer'].get('bridge', False)
            report['passed'] = bool(report['web_loaded'] and report['javascript_bridge']
                                    and report['renderer'].get('canvas') and report['renderer'].get('animation_frames', 0) > 30
                                    and not report['renderer'].get('errors'))
            if args.require_audio:
                report['passed'] &= bool(audio.frames > 0 and not audio.error and
                                         report['renderer'].get('frames', 0) > 0)
            if args.play_test_tone:
                report['passed'] &= bool(audio.peak_rms > .0001 and abs(audio.peak_hz - 1000) < 50)
            if args.gallery:
                report['passed'] &= len(set(report['themes'].values())) == 6
            args.self_test.parent.mkdir(parents=True, exist_ok=True)
            window.grab().save(str(args.self_test.with_suffix('.png')))
            stopped = audio.stop()
            report['audio_stopped'] = stopped
            report['passed'] &= stopped
            args.self_test.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf8')
            window.close()
            app.exit(0 if report['passed'] else 1)
        window.web.page().runJavaScript(script, result)
    QTimer.singleShot(13000 if args.gallery else 7000, finish)
    QTimer.singleShot(20000, lambda: app.exit(2))
