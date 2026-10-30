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
    if args.format_test:
        from format_probe import start
        start(window, report)
    if args.studio_test:
        from PySide6.QtCore import QUrl
        from PySide6.QtWebEngineWidgets import QWebEngineView
        window.live_view = QWebEngineView()
        window.live_view.resize(540, 960)
        window.live_view.load(QUrl(window.live.url))
        window.live_view.show()
        report['independent_source'] = []

        def sample_live():
            script = 'JSON.stringify({frames:window.sceneEngine.frameCount,audio:window.audioDiagnostics,errors:window.jsErrors,track:document.querySelector("[data-kind=track] .placed-content").textContent,logo:document.querySelector("[data-kind=logo] img").naturalWidth,background:!!window.sceneEngine.backgroundImage})'
            def sampled(value):
                if value:
                    report['independent_source'].append(json.loads(value))
            window.live_view.page().runJavaScript(script, sampled)
        for second in range(2, 15):
            QTimer.singleShot(second * 1000, sample_live)
        QTimer.singleShot(3500, window.showMinimized)
        QTimer.singleShot(8000, window.hide)
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
        from process_audio import library, supported
        try:
            library()
            report['native_audio_bridge_loaded'] = True
        except Exception as exc:
            report['native_audio_bridge_loaded'] = False
            report['native_audio_bridge_error'] = str(exc)
        report['application_capture_supported'] = supported()
        report['source_mode'] = window.selected_source.get('mode')
        if audio is None:
            report.update(passed=False, audio_error=window.last_status)
            args.self_test.write_text(json.dumps(report, indent=2), encoding='utf8')
            window.close()
            app.exit(1)
            return
        report.update(device=audio.device, captured_frames=audio.frames,
                      sample_rate=audio.sample_rate, peak_rms=audio.peak_rms,
                      peak_hz=audio.peak_hz, audio_error=audio.error)
        script = "JSON.stringify({bridge:!!window.desktopBridge,active:window.desktopAudioActive,frames:window.desktopFrameCount,animation_frames:window.sceneEngine.frameCount,animation_time:window.sceneEngine.time,canvas:document.getElementById('visual').width,audio:window.audioDiagnostics,visual_response:window.verifyAudioRendering(),errors:window.jsErrors||[]})"

        def result(value):
            report['renderer'] = json.loads(value) if value else {}
            report['javascript_bridge'] = report['renderer'].get('bridge', False)
            report['passed'] = bool(report['web_loaded'] and report['javascript_bridge']
                                    and report['native_audio_bridge_loaded']
                                    # The format probe intentionally hides the controls.
                                    # Its two independent sources must keep advancing;
                                    # the hidden controls only need to have rendered once.
                                    and report['renderer'].get('canvas') and report['renderer'].get('animation_frames', 0) > (0 if args.format_test else 30)
                                    and not report['renderer'].get('errors'))
            report['passed'] &= all(item['changedFraction'] > .025 for item in report['renderer']['visual_response'].values())
            if args.require_audio:
                report['passed'] &= bool(audio.frames > 0 and not audio.error and
                                         report['renderer'].get('frames', 0) > 0)
            if args.play_test_tone:
                report['passed'] &= bool(audio.peak_rms > .0001 and abs(audio.peak_hz - 1000) < 50)
            if args.expect_tone_hz is not None:
                report['passed'] &= bool(audio.peak_rms > .0001 and abs(audio.peak_hz - args.expect_tone_hz) < 30)
            if args.gallery:
                report['passed'] &= len(set(report['themes'].values())) == 6
            if args.format_test:
                from format_probe import finish as finish_formats
                report['format_screenshot_base'] = args.self_test
                report['passed'] &= finish_formats(window, report)
                del report['format_screenshot_base']
            if args.studio_test:
                samples = report['independent_source']
                report['background_continuity'] = bool(len(samples) >= 10 and
                    samples[-1]['frames'] > samples[0]['frames'] + 100 and
                    samples[-1]['audio'].get('signal') and
                    sum(bool(s['audio'].get('signal')) for s in samples) >= 5 and
                    all(not s['errors'] for s in samples))
                report['packaged_logo'] = window.windowIcon().isNull() is False
                report['passed'] &= report['background_continuity'] and report['packaged_logo']
                window.live_view.grab().save(str(args.self_test.with_name(args.self_test.stem + '-live.png')))
            args.self_test.parent.mkdir(parents=True, exist_ok=True)
            window.grab().save(str(args.self_test.with_suffix('.png')))
            stopped = audio.stop()
            report['audio_stopped'] = stopped
            report['passed'] &= stopped
            args.self_test.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf8')
            window.close()
            app.exit(0 if report['passed'] else 1)
        window.web.page().runJavaScript(script, result)
    QTimer.singleShot(15500 if args.studio_test else 13000 if args.gallery else 11000 if args.format_test else 7000, finish)
    QTimer.singleShot(25000 if args.studio_test else 20000, lambda: app.exit(2))
