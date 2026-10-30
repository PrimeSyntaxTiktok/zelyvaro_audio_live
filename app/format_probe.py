"""Opt-in end-to-end checks for copy-link formats and close-to-tray behavior."""
import json
from urllib.parse import parse_qs, urlsplit
from PySide6.QtCore import QTimer, QUrl, QMimeData
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication
from stream_format import StreamFormatDialog, FORMATS


def start(window, report):
    clipboard = QApplication.clipboard()
    original = QMimeData()
    previous = clipboard.mimeData()
    for kind in previous.formats() if previous else []:
        original.setData(kind, previous.data(kind))
    window._format_last_clipboard = None
    def restore_clipboard():
        if clipboard.text() == window._format_last_clipboard:
            clipboard.setMimeData(original)
            window._format_last_clipboard = None
    window.restore_probe_clipboard = restore_clipboard
    QApplication.instance().aboutToQuit.connect(restore_clipboard)
    checks = report['format_test'] = {'copies': {}, 'views': {}, 'errors': []}
    window.format_views = {}
    for mode in FORMATS:
        view = QWebEngineView()
        view.resize(800, 450)
        view.setWindowTitle('Diagnostic ' + mode)
        view.load(QUrl(window.live.formatted_url(mode)))
        view.show()
        window.format_views[mode] = view

    def copy(mode, cancel=False):
        before = QApplication.clipboard().text()
        def choose():
            dialog = QApplication.activeModalWidget()
            if not isinstance(dialog, StreamFormatDialog):
                checks['errors'].append('Format dialog unavailable')
                return
            checks['copies'][mode + ('_cancel' if cancel else '')] = {'initial': dialog.selected_format}
            dialog.choices[mode].click()
            dialog.reject() if cancel else dialog.accept()
        QTimer.singleShot(100, choose)
        window.copy_stream_link()
        after = QApplication.clipboard().text()
        if not cancel:
            window._format_last_clipboard = after
        if cancel:
            checks['cancel_preserves_clipboard'] = before == after
            checks['cancel_preserves_format'] = window.stream_format == 'portrait'
        else:
            checks['copies'][mode]['copied_format'] = parse_qs(urlsplit(after).query).get('format', [''])[0]
            checks['copies'][mode]['saved'] = window.stream_format

    QTimer.singleShot(1000, lambda: copy('landscape'))
    QTimer.singleShot(1800, lambda: copy('portrait'))
    QTimer.singleShot(2600, lambda: copy('landscape', True))

    def check_studio():
        script = '''(()=>{const states=[];for(const tab of document.querySelectorAll('[data-pane]')){tab.click();states.push(document.querySelectorAll('.settings-pane:not([hidden])').length===1&&tab.getAttribute('aria-selected')==='true');}window.applyVisualSettings({overlays:{track:{mode:'manual',manualArtist:'Artiste test',manualTitle:'Titre test',visible:true,locked:true,weight:400}}});window.overlayController.refresh();const n=document.querySelector('[data-kind=track]'),label=n.querySelector('.track-label');return JSON.stringify({tabs:states.length===4&&states.every(Boolean),track:label?.textContent,bold:getComputedStyle(n).fontWeight==='700',singleLine:label?.getClientRects().length===1,transparentMusicIcon:!!n.querySelector('svg.music-icon[fill=none]'),errors:window.jsErrors});})()'''
        window.web.page().runJavaScript(script, lambda value: checks.__setitem__('studio', json.loads(value) if value else {}))
    QTimer.singleShot(2900, check_studio)

    def close_to_tray():
        window.probe = False
        window.close()
        checks['close_keeps_running'] = not window.live.stopping and (window.isHidden() or window.isMinimized())
        window.probe = True
        window.tray.hide()
    QTimer.singleShot(3200, close_to_tray)

    def snapshot(tag):
        script = '''(()=>{const f=document.getElementById('stage'),w=f?.contentWindow,r=f?.getBoundingClientRect(),c=w?.document.getElementById('visual')?.getBoundingClientRect();return JSON.stringify({hostWidth:innerWidth,hostHeight:innerHeight,width:w?.innerWidth,height:w?.innerHeight,frames:w?.sceneEngine?.frameCount||0,rect:r?{x:r.x,y:r.y,w:r.width,h:r.height}:null,canvas:c?{x:c.x,y:c.y,w:c.width,h:c.height}:null,edgesCovered:[[1,1],[innerWidth-1,1],[1,innerHeight-1],[innerWidth-1,innerHeight-1]].every(([x,y])=>document.elementFromPoint(x,y)===f),errors:w?.jsErrors||[]});})()'''
        for mode, view in window.format_views.items():
            view.page().runJavaScript(script, lambda value, mode=mode: checks['views'].setdefault(mode, {}).__setitem__(tag, json.loads(value) if value else {}))
    QTimer.singleShot(4200, lambda: snapshot('first'))
    QTimer.singleShot(6000, lambda: window.format_views['portrait'].resize(450, 800))
    QTimer.singleShot(8500, lambda: snapshot('last'))


def finish(window, report):
    checks = report['format_test']
    passed = bool(not checks['errors'] and checks.get('close_keeps_running') and
                  checks.get('cancel_preserves_clipboard') and checks.get('cancel_preserves_format'))
    studio = checks.get('studio', {})
    passed &= bool(studio.get('tabs') and studio.get('bold') and studio.get('singleLine') and
                   studio.get('transparentMusicIcon') and studio.get('track') == 'Artiste test — Titre test' and not studio.get('errors'))
    for mode, (_, width, height, _) in FORMATS.items():
        item = checks['views'].get(mode, {})
        first, last = item.get('first', {}), item.get('last', {})
        copied = checks['copies'].get(mode, {})
        passed &= bool(copied.get('copied_format') == mode and copied.get('saved') == mode and
                       first.get('frames', 0) > 0 and last.get('frames', 0) > first.get('frames', 0) + 5 and
                       not last.get('errors'))
        for sample in (first, last):
            rect, canvas = sample.get('rect', {}), sample.get('canvas', {})
            passed &= bool(sample.get('edgesCovered') and sample.get('width') == sample.get('hostWidth') and
                           sample.get('height') == sample.get('hostHeight') and
                           rect.get('x') == rect.get('y') == canvas.get('x') == canvas.get('y') == 0 and
                           rect.get('w') == canvas.get('w') == sample.get('hostWidth') and
                           rect.get('h') == canvas.get('h') == sample.get('hostHeight'))
        path = report.get('format_screenshot_base')
        if path:
            window.format_views[mode].grab().save(str(path.with_name(path.stem + '-' + mode + '.png')))
        window.format_views[mode].close()
    checks['remembered_landscape'] = checks['copies'].get('portrait', {}).get('initial') == 'landscape'
    checks['passed'] = passed and checks['remembered_landscape']
    window.restore_probe_clipboard()
    return checks['passed']
