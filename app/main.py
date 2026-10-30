"""ZELYVARO Audio Live Windows application."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = (os.environ.get('QTWEBENGINE_CHROMIUM_FLAGS', '') +
    ' --disable-background-timer-throttling --disable-renderer-backgrounding --disable-backgrounding-occluded-windows').strip()

from PySide6.QtCore import QObject, QTimer, QUrl, Signal, Slot, Qt
from PySide6.QtGui import QShortcut, QKeySequence, QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QFileDialog, QSystemTrayIcon, QMenu, QStyle, QDialog
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage

from audio import AudioThread
from process_audio import applications, resolve_source, media_info
from source_dialog import SourceDialog
from stream_format import StreamFormatDialog, FORMATS, format_dimensions
from single_instance import SingleInstance, activate_legacy_instance
import background
from live_server import LiveServer, preserve_existing_port
from visual_settings import validated
from updates import latest_update, download_update
from version import VERSION, APP, REPOSITORY

BASE = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
DATA_DIR = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'ZelyvaroAudioLive'


class Bridge(QObject):
    restartRequested = Signal()
    sourceRequested = Signal()
    backgroundRequested = Signal()
    backgroundCleared = Signal()
    visualSettingsChanged = Signal(str)
    visualReadyRequested = Signal()
    streamLinkRequested = Signal()
    logoRequested = Signal()
    logoUrlRequested = Signal(str)
    logoCleared = Signal()
    liveExitRequested = Signal()
    defaultLogoRequested = Signal()
    fullscreenRequested = Signal()
    cleanChanged = Signal(bool)

    @Slot()
    def restartAudio(self):
        self.restartRequested.emit()

    @Slot()
    def chooseAudio(self):
        self.sourceRequested.emit()

    @Slot()
    def chooseBackground(self):
        self.backgroundRequested.emit()

    @Slot()
    def clearBackground(self):
        self.backgroundCleared.emit()

    @Slot(str)
    def updateVisualSettings(self, value):
        self.visualSettingsChanged.emit(value)

    @Slot()
    def visualReady(self):
        self.visualReadyRequested.emit()

    @Slot()
    def copyStreamLink(self):
        self.streamLinkRequested.emit()

    @Slot()
    def chooseLogo(self):
        self.logoRequested.emit()

    @Slot(str)
    def importLogoUrl(self, value):
        self.logoUrlRequested.emit(value)

    @Slot()
    def clearLogo(self):
        self.logoCleared.emit()

    @Slot()
    def exitLive(self):
        self.liveExitRequested.emit()

    @Slot()
    def useDefaultLogo(self):
        self.defaultLogoRequested.emit()

    @Slot()
    def toggleFullscreen(self):
        self.fullscreenRequested.emit()

    @Slot(bool)
    def setClean(self, clean):
        self.cleanChanged.emit(clean)


class MainWindow(QMainWindow):
    metadataFound = Signal(object)
    logoImported = Signal(object)
    logoFailed = Signal(str)
    updateFound = Signal(object)
    updateMessage = Signal(str)
    downloadComplete = Signal(str)
    progressChanged = Signal(int)
    checkFinished = Signal()
    downloadFailed = Signal(str)

    def __init__(self, probe=False, source=None):
        super().__init__()
        self.setWindowTitle(f'{APP} {VERSION}')
        self.setWindowIcon(QIcon(str(BASE / 'app.ico')))
        self.resize(450, 800)
        self.setMinimumSize(270, 480)
        self.audio = None
        self.pending = None
        self.ready = False
        self.checking = False
        self.downloading = False
        self.probe = probe
        try:
            output = json.loads((DATA_DIR / 'stream-output.json').read_text(encoding='utf8'))
            self.stream_format = output['format'] if output.get('format') in FORMATS else 'portrait'
        except (OSError, ValueError, KeyError, TypeError):
            self.stream_format = 'portrait'
        self._quitting = False
        self._metadata_stop = threading.Event()
        self.track_metadata = {'artist': '', 'title': '', 'available': False}
        try:
            self.visual_settings = validated(json.loads((DATA_DIR / 'visual-settings.json').read_text(encoding='utf8')))
        except (OSError, ValueError):
            self.visual_settings = {}
        self.live = LiveServer(BASE, DATA_DIR)
        self.live.publish('settings', self.visual_settings)
        self.live.publish('background', background.state(DATA_DIR))
        self.live.publish('logo', background.state(DATA_DIR / 'logo'))
        self.live.publish('track', self.track_metadata)
        self.selected_source = source or {'mode': 'system', 'name': 'Tout le son Windows'}
        if source is None and not probe:
            try:
                saved = json.loads((DATA_DIR / 'audio-source.json').read_text(encoding='utf8'))
                if saved.get('mode') == 'application' and saved.get('path'):
                    self.selected_source = saved
            except (OSError, ValueError, AttributeError):
                pass
        self.last_status = 'Capture Windows en cours de démarrage…'
        self.web = QWebEngineView()
        self.web.page().setLifecycleState(QWebEnginePage.LifecycleState.Active)
        self.setCentralWidget(self.web)
        self.bridge = Bridge()
        self.channel = QWebChannel(self.web.page())
        self.channel.registerObject('desktopBridge', self.bridge)
        self.web.page().setWebChannel(self.channel)
        self.bridge.restartRequested.connect(self.start_audio)
        self.bridge.sourceRequested.connect(self.choose_audio)
        self.bridge.backgroundRequested.connect(self.choose_background)
        self.bridge.backgroundCleared.connect(self.clear_background)
        self.bridge.visualSettingsChanged.connect(self.update_visual_settings)
        self.bridge.visualReadyRequested.connect(self.send_visual_state)
        self.bridge.streamLinkRequested.connect(self.copy_stream_link)
        self.bridge.logoRequested.connect(self.choose_logo)
        self.bridge.logoUrlRequested.connect(self.import_logo_url)
        self.bridge.logoCleared.connect(self.clear_logo)
        self.bridge.liveExitRequested.connect(self.exit_live)
        self.bridge.defaultLogoRequested.connect(self.use_default_logo)
        self.metadataFound.connect(self.update_metadata)
        self.logoImported.connect(lambda value: self.send_logo())
        self.logoFailed.connect(lambda text: QMessageBox.warning(self, 'Logo', text))
        self.escape_shortcut = QShortcut(QKeySequence('Escape'), self)
        self.escape_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.escape_shortcut.activated.connect(self.exit_live)
        self.bridge.fullscreenRequested.connect(self.toggle_fullscreen)
        self.bridge.cleanChanged.connect(lambda clean: self.menuBar().setVisible(not clean))
        self.web.loadFinished.connect(self.on_loaded)
        self.web.load(QUrl.fromLocalFile(str(BASE / 'wallpaper.html')))
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.flush_audio)
        self.timer.start(25)
        self.resolution_timer = QTimer(self)
        self.resolution_timer.timeout.connect(self.send_stream_diagnostics)
        self.resolution_timer.start(1000)
        audio_menu = self.menuBar().addMenu('Audio')
        audio_menu.addAction('Choisir l’application audio…', self.choose_audio)
        audio_menu.addAction('Relancer la capture', self.start_audio)
        appearance_menu = self.menuBar().addMenu('Apparence')
        appearance_menu.addAction('Choisir une image de fond…', self.choose_background)
        appearance_menu.addAction('Retirer l’image de fond', self.clear_background)
        stream_menu = self.menuBar().addMenu('Diffusion')
        stream_menu.addAction('Copier le lien TikTok / OBS', self.copy_stream_link)
        stream_menu.addAction('Ouvrir la sortie de diffusion', self.open_live_output)
        stream_menu.addAction('Réduire en zone de notification', self.hide)
        stream_menu.addSeparator()
        stream_menu.addAction('Quitter le logiciel', self.quit_application)
        self.update_action = self.menuBar().addAction('Vérifier les mises à jour', lambda: self.check_updates(False))
        self.menuBar().addAction('Mode Live (H)', lambda: self.web.page().runJavaScript('window.toggleClean()'))
        self.updateFound.connect(self.install_update)
        self.updateMessage.connect(lambda msg: QMessageBox.information(self, 'Mises à jour', msg))
        self.downloadComplete.connect(self.launch_installer)
        self.downloadFailed.connect(self.download_error)
        self.progressChanged.connect(lambda value: self.statusBar().showMessage(f'Téléchargement de la mise à jour : {value} %'))
        self.checkFinished.connect(self.check_finished)
        self.tray = QSystemTrayIcon(self.windowIcon(), self)
        self.tray.setToolTip('ZELYVARO Audio Live — capture et diffusion actives')
        tray_menu = QMenu(self)
        self.tray_menu = tray_menu
        tray_menu.addAction('Afficher les réglages', self.restore_window)
        tray_menu.addAction('Copier le lien de diffusion', self.copy_stream_link)
        tray_menu.addSeparator()
        tray_menu.addAction('Quitter', self.quit_application)
        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(lambda reason: self.restore_window() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
        if not probe:
            self.tray.show()
        self.start_audio()
        self.metadata_thread = threading.Thread(target=self.poll_metadata, daemon=True)
        self.metadata_thread.start()
        if not probe:
            self.source_timer = QTimer(self)
            self.source_timer.timeout.connect(self.reconnect_source)
            self.source_timer.start(5000)
            QTimer.singleShot(3000, lambda: self.check_updates(True))
            self.update_timer = QTimer(self)
            self.update_timer.timeout.connect(lambda: self.check_updates(True))
            self.update_timer.start(4 * 60 * 60 * 1000)

    def toggle_fullscreen(self):
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def on_loaded(self, ok):
        self.ready = ok
        if ok:
            self.web.page().runJavaScript('window.setDesktopStatus(' + json.dumps(self.last_status) + ')')
            self.send_background()
            self.send_logo()
            self.send_visual_state()
        elif not self.probe:
            QMessageBox.critical(self, APP, 'Impossible de charger le fond animé livré avec le logiciel.')

    def start_audio(self):
        if self.audio is not None and not self.audio.stop():
            self.set_status('La capture précédente ne répond pas. Réessayez.')
            return
        previous = self.audio
        self.audio = None
        if previous is not None:
            previous.deleteLater()
        self.pending = None
        if self.ready:
            self.web.page().runJavaScript('window.clearDesktopAudio()')
        if self.selected_source.get('mode') == 'application':
            try:
                resolved = resolve_source(self.selected_source, applications())
            except Exception as exc:
                self.set_status('Source audio indisponible : ' + str(exc))
                return
            if resolved is None:
                self.set_status(self.selected_source.get('name', 'Application') + ' — en attente de l’application')
                return
            self.selected_source = resolved
        self.set_status('Capture Windows en cours de démarrage…')
        worker = AudioThread(self, self.selected_source)
        self.audio = worker
        worker.spectrumReady.connect(lambda values: self.receive_audio(values) if self.audio is worker else None)
        worker.status.connect(lambda status: self.set_status(status) if self.audio is worker else None)
        worker.issue.connect(lambda issue: self.audio_error(issue) if self.audio is worker else None)
        worker.start()

    def choose_audio(self):
        dialog = SourceDialog(self.selected_source, self)
        if dialog.exec() != SourceDialog.DialogCode.Accepted:
            return
        source = dialog.source()
        if source is None:
            return
        self.selected_source = source
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        temporary = DATA_DIR / 'audio-source.json.tmp'
        temporary.write_text(json.dumps(source, ensure_ascii=False, indent=2), encoding='utf8')
        temporary.replace(DATA_DIR / 'audio-source.json')
        self.start_audio()

    def reconnect_source(self):
        if self.selected_source.get('mode') == 'application' and (self.audio is None or not self.audio.isRunning()):
            self.start_audio()

    def receive_audio(self, values):
        self.pending = values
        self.live.publish('audio', values)

    def update_visual_settings(self, text):
        if len(text) > 65536:
            return
        try:
            settings = validated(json.loads(text))
        except (ValueError, TypeError):
            return
        self.visual_settings = settings
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        temporary = DATA_DIR / 'visual-settings.tmp.json'
        temporary.write_text(json.dumps(settings, ensure_ascii=False), encoding='utf8')
        temporary.replace(DATA_DIR / 'visual-settings.json')
        self.live.publish('settings', settings)

    def send_visual_state(self):
        if self.ready:
            self.web.page().runJavaScript('window.setStreamUrl(' + json.dumps(self.live.url) + ')')
            if self.visual_settings:
                self.web.page().runJavaScript('window.applyVisualSettings(' + json.dumps(self.visual_settings) + ')')
            else:
                self.web.page().runJavaScript('window.syncCurrentSettings()')
            self.web.page().runJavaScript('window.setTrackMetadata(' + json.dumps(self.track_metadata) + ')')

    def poll_metadata(self):
        while not self._metadata_stop.is_set():
            source = self.selected_source.copy()
            hint = Path(source.get('path', '')).stem if source.get('mode') == 'application' else ''
            try:
                result = media_info(hint)
            except Exception:
                result = {'artist': '', 'title': '', 'available': False}
            result['source'] = hint
            if not self._metadata_stop.is_set():
                self.metadataFound.emit(result)
            self._metadata_stop.wait(2)

    def update_metadata(self, value):
        hint = Path(self.selected_source.get('path', '')).stem if self.selected_source.get('mode') == 'application' else ''
        if value.get('source', hint) != hint:
            return
        self.track_metadata = value
        self.live.publish('track', value)
        if self.ready:
            self.web.page().runJavaScript('window.setTrackMetadata(' + json.dumps(value) + ')')

    def exit_live(self):
        if self.isFullScreen():
            self.showNormal()
        if not self.isVisible():
            self.restore_window()
        self.menuBar().show()
        if self.ready:
            self.web.page().runJavaScript('window.exitLiveMode()')

    def choose_logo(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Choisir mon logo', '',
                                                 'Images (*.png *.jpg *.jpeg *.webp *.bmp)')
        if filename:
            try:
                background.import_background(filename, DATA_DIR / 'logo')
                self.send_logo()
            except (ValueError, OSError) as exc:
                QMessageBox.warning(self, 'Logo', str(exc))

    def import_logo_url(self, url):
        def download():
            try:
                result = background.import_url(url, DATA_DIR / 'logo')
                self.logoImported.emit(result)
            except Exception as exc:
                self.logoFailed.emit(str(exc))
        threading.Thread(target=download, daemon=True).start()

    def send_logo(self):
        value = background.state(DATA_DIR / 'logo')
        self.live.publish('logo', value)
        if self.ready:
            self.web.page().runJavaScript('window.setLogoImage(' + json.dumps(value) + ')')

    def clear_logo(self):
        background.clear(DATA_DIR / 'logo')
        self.send_logo()

    def use_default_logo(self):
        background.import_background(BASE / 'logo.png', DATA_DIR / 'logo')
        self.send_logo()

    def copy_stream_link(self):
        dialog = StreamFormatDialog(self.stream_format, self, self.visual_settings.get('quality', '4k'))
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.stream_format = dialog.selected_format
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        pending = DATA_DIR / 'stream-output.tmp.json'
        pending.write_text(json.dumps({'format': self.stream_format}), encoding='utf8')
        pending.replace(DATA_DIR / 'stream-output.json')
        QApplication.clipboard().setText(self.live.formatted_url(self.stream_format))
        label, width, height, _ = format_dimensions(self.stream_format, self.visual_settings.get('quality', '4k'))
        message = f'Lien {label.lower()} copié · {width} × {height}'
        self.statusBar().showMessage(message, 8000)
        self.web.page().runJavaScript('window.setStreamCopied(' + json.dumps(message) + ')')

    def send_stream_diagnostics(self):
        if self.ready:
            self.web.page().runJavaScript('window.setStreamDiagnostics?.(' + json.dumps(self.live.viewport_state()) + ',' + str(self.live.clients) + ')')

    def open_live_output(self):
        if not hasattr(self, 'live_view'):
            self.live_view = QWebEngineView()
            self.live_view.setWindowTitle('ZELYVARO — Sortie de diffusion')
            self.live_view.setWindowIcon(self.windowIcon())
            self.live_view.page().setLifecycleState(QWebEnginePage.LifecycleState.Active)
        _, width, height, _ = FORMATS[self.stream_format]
        self.live_view.resize(450, 800) if width < height else self.live_view.resize(960, 540)
        self.live_view.load(QUrl(self.live.formatted_url(self.stream_format)))
        self.live_view.show()

    def restore_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def send_background(self):
        value = background.state(DATA_DIR)
        self.live.publish('background', value)
        if self.ready:
            self.web.page().runJavaScript('window.setBackgroundImage(' + json.dumps(value, ensure_ascii=True) + ')')

    def choose_background(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Choisir mon image de fond', '',
                                                 'Images (*.png *.jpg *.jpeg *.webp *.bmp)')
        if not filename:
            return
        try:
            background.import_background(filename, DATA_DIR)
            self.send_background()
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, 'Image de fond', str(exc))

    def clear_background(self):
        background.clear(DATA_DIR)
        self.send_background()

    def set_status(self, status):
        self.last_status = status
        self.live.publish('status', status)
        if self.ready:
            self.web.page().runJavaScript('window.setDesktopStatus(' + json.dumps(status) + ')')

    def flush_audio(self):
        if self.ready and self.pending is not None:
            values, self.pending = self.pending, None
            self.web.page().runJavaScript('window.setDesktopAudio(' + json.dumps(values) + ')')

    def audio_error(self, issue):
        self.pending = None
        self.set_status('Capture indisponible — cliquer pour relancer')
        if self.ready:
            self.web.page().runJavaScript('window.clearDesktopAudio()')
        self.live.publish('audio', {'bands': [0] * 128, 'waveform': [0] * 256, 'signal': False,
                                   'level': 0, 'bass': 0, 'mid': 0, 'treble': 0, 'rmsDb': -140})
        if self.selected_source.get('mode') == 'application':
            self.set_status(self.selected_source.get('name', 'Application') + ' — capture interrompue : ' + issue)
        elif not self.probe:
            QMessageBox.warning(self, 'Capture audio Windows', issue + '\n\nActivez une sortie audio Windows, puis utilisez « Relancer capture audio ».')

    def check_updates(self, silent):
        if self.checking or self.downloading:
            return
        self.checking = True
        self.update_action.setEnabled(False)

        def worker():
            try:
                update = latest_update()
                if update:
                    self.updateFound.emit(update)
                elif not silent:
                    self.updateMessage.emit(f'Version {VERSION} : aucune version stable plus récente sur {REPOSITORY}.')
            except Exception as exc:
                if not silent:
                    self.updateMessage.emit('Vérification impossible : ' + str(exc))
            finally:
                self.checkFinished.emit()
        threading.Thread(target=worker, daemon=True).start()

    def check_finished(self):
        self.checking = False
        self.update_action.setEnabled(not self.downloading)

    def install_update(self, update):
        if not getattr(sys, 'frozen', False):
            self.updateMessage.emit(f'Version {update.version} disponible. Utilisez la version installée pour la mise à jour.')
            return
        answer = QMessageBox.question(self, 'Mise à jour disponible',
            f'Installer ZELYVARO Audio Live {update.version} depuis GitHub Releases ?\n\n'
            'Le logiciel se fermera après vérification du téléchargement, puis redémarrera. Vos réglages seront conservés.')
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.downloading = True
        self.update_action.setEnabled(False)

        def download():
            try:
                path = download_update(update, DATA_DIR / 'updates', self.progressChanged.emit)
                self.downloadComplete.emit(str(path))
            except Exception as exc:
                self.downloadFailed.emit(str(exc))
        threading.Thread(target=download, daemon=True).start()

    def download_error(self, error):
        self.downloading = False
        self.update_action.setEnabled(True)
        self.statusBar().clearMessage()
        self.updateMessage.emit('Mise à jour annulée : ' + error)

    def launch_installer(self, path):
        args = [path, '/SILENT', '/SP-', '/CLOSEAPPLICATIONS', '/RESTARTAPPLICATIONS', '/UPDATE=1',
                '/DIR=' + str(Path(sys.executable).parent)]
        try:
            subprocess.Popen(args, close_fds=True)
        except OSError as exc:
            self.download_error(str(exc))
            return
        self.quit_application()

    def quit_application(self):
        self._quitting = True
        self.close()
        QApplication.quit()

    def closeEvent(self, event):
        if not self.probe and not self._quitting:
            if QSystemTrayIcon.isSystemTrayAvailable():
                self.tray.show()
                self.hide()
            else:
                self.showMinimized()
            event.ignore()
            return
        self._metadata_stop.set()
        if self.audio is not None and not self.audio.stop():
            event.ignore()
            return
        self.tray.hide()
        self.live.close()
        if hasattr(self, 'live_view'):
            self.live_view.close()
        event.accept()
        if not self.probe:
            QTimer.singleShot(0, QApplication.quit)


def main():
    global DATA_DIR
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test', type=Path)
    parser.add_argument('--play-test-tone', action='store_true')
    parser.add_argument('--require-audio', action='store_true')
    parser.add_argument('--gallery', action='store_true')
    parser.add_argument('--source-pid', type=int)
    parser.add_argument('--expect-tone-hz', type=float)
    parser.add_argument('--test-profile', type=Path)
    parser.add_argument('--studio-test', action='store_true')
    parser.add_argument('--format-test', action='store_true')
    args = parser.parse_args()
    if (args.test_profile or args.studio_test or args.format_test) and not args.self_test:
        parser.error('Les options de diagnostic nécessitent --self-test.')
    if args.test_profile:
        DATA_DIR = args.test_profile.resolve()
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('ZELYVARO.AudioLive')
    app = QApplication([sys.argv[0]])
    app.setWindowIcon(QIcon(str(BASE / 'app.ico')))
    app.setQuitOnLastWindowClosed(False)
    app.setOrganizationName('ZELYVARO')
    # Keep opt-in diagnostics out of the normal WebEngine preference/cache profile.
    # The executable/process name remains unchanged.
    app.setApplicationName('ZelyvaroAudioLive-Diagnostics' if args.self_test else 'ZelyvaroAudioLive')
    app.setApplicationVersion(VERSION)
    instance = None
    if not args.self_test:
        instance = SingleInstance(DATA_DIR)
        if not instance.acquire():
            return 0
        if activate_legacy_instance():
            preserve_existing_port(DATA_DIR)
            instance.close()
            return 0
        app.aboutToQuit.connect(instance.close)
    source = None
    if args.source_pid:
        source = next((item for item in applications() if item['pid'] == args.source_pid), None)
        if source is None:
            raise RuntimeError('Cette application n’a pas de session audio Windows disponible.')
    try:
        window = MainWindow(probe=bool(args.self_test), source=source)
    except (OSError, ValueError, KeyError) as exc:
        if instance:
            instance.close()
        if not args.self_test:
            QMessageBox.warning(None, APP, 'La diffusion ne peut pas démarrer.\n\n' + str(exc))
        return 1
    if instance:
        instance.bind(window.restore_window)
    window.show()
    if args.self_test:
        from probe import run_probe
        run_probe(app, window, args)
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
