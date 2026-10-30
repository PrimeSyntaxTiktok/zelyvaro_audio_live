"""ZELYVARO Audio Live Windows application."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

from PySide6.QtCore import QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

from audio import AudioThread
from process_audio import applications, resolve_source
from source_dialog import SourceDialog
from updates import latest_update, download_update
from version import VERSION, APP, REPOSITORY

BASE = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
DATA_DIR = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'ZelyvaroAudioLive'


class Bridge(QObject):
    restartRequested = Signal()
    sourceRequested = Signal()
    fullscreenRequested = Signal()
    cleanChanged = Signal(bool)

    @Slot()
    def restartAudio(self):
        self.restartRequested.emit()

    @Slot()
    def chooseAudio(self):
        self.sourceRequested.emit()

    @Slot()
    def toggleFullscreen(self):
        self.fullscreenRequested.emit()

    @Slot(bool)
    def setClean(self, clean):
        self.cleanChanged.emit(clean)


class MainWindow(QMainWindow):
    updateFound = Signal(object)
    updateMessage = Signal(str)
    downloadComplete = Signal(str)
    progressChanged = Signal(int)
    checkFinished = Signal()
    downloadFailed = Signal(str)

    def __init__(self, probe=False, source=None):
        super().__init__()
        self.setWindowTitle(f'{APP} {VERSION}')
        self.resize(450, 800)
        self.setMinimumSize(270, 480)
        self.audio = None
        self.pending = None
        self.ready = False
        self.checking = False
        self.downloading = False
        self.probe = probe
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
        self.setCentralWidget(self.web)
        self.bridge = Bridge()
        self.channel = QWebChannel(self.web.page())
        self.channel.registerObject('desktopBridge', self.bridge)
        self.web.page().setWebChannel(self.channel)
        self.bridge.restartRequested.connect(self.start_audio)
        self.bridge.sourceRequested.connect(self.choose_audio)
        self.bridge.fullscreenRequested.connect(self.toggle_fullscreen)
        self.bridge.cleanChanged.connect(lambda clean: self.menuBar().setVisible(not clean))
        self.web.loadFinished.connect(self.on_loaded)
        self.web.load(QUrl.fromLocalFile(str(BASE / 'wallpaper.html')))
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.flush_audio)
        self.timer.start(40)
        audio_menu = self.menuBar().addMenu('Audio')
        audio_menu.addAction('Choisir l’application audio…', self.choose_audio)
        audio_menu.addAction('Relancer la capture', self.start_audio)
        self.update_action = self.menuBar().addAction('Vérifier les mises à jour', lambda: self.check_updates(False))
        self.menuBar().addAction('Mode Live (H)', lambda: self.web.page().runJavaScript('window.toggleClean()'))
        self.updateFound.connect(self.install_update)
        self.updateMessage.connect(lambda msg: QMessageBox.information(self, 'Mises à jour', msg))
        self.downloadComplete.connect(self.launch_installer)
        self.downloadFailed.connect(self.download_error)
        self.progressChanged.connect(lambda value: self.statusBar().showMessage(f'Téléchargement de la mise à jour : {value} %'))
        self.checkFinished.connect(self.check_finished)
        self.start_audio()
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

    def set_status(self, status):
        self.last_status = status
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
        self.close()

    def closeEvent(self, event):
        if self.audio is not None and not self.audio.stop():
            event.ignore()
            return
        event.accept()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test', type=Path)
    parser.add_argument('--play-test-tone', action='store_true')
    parser.add_argument('--require-audio', action='store_true')
    parser.add_argument('--gallery', action='store_true')
    parser.add_argument('--source-pid', type=int)
    parser.add_argument('--expect-tone-hz', type=float)
    args = parser.parse_args()
    app = QApplication([sys.argv[0]])
    app.setOrganizationName('ZELYVARO')
    app.setApplicationName('ZelyvaroAudioLive')
    app.setApplicationVersion(VERSION)
    source = None
    if args.source_pid:
        source = next((item for item in applications() if item['pid'] == args.source_pid), None)
        if source is None:
            raise RuntimeError('Cette application n’a pas de session audio Windows disponible.')
    window = MainWindow(probe=bool(args.self_test), source=source)
    window.show()
    if args.self_test:
        from probe import run_probe
        run_probe(app, window, args)
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
