"""ZELYVARO Audio Live - Windows WASAPI loopback visualizer."""
import json
import os
import sys
import subprocess
import tempfile
import threading
import urllib.request
from pathlib import Path

import numpy as np
from packaging.version import Version
from PySide6.QtCore import QThread, QTimer, QUrl, Signal
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PySide6.QtWebEngineWidgets import QWebEngineView

VERSION = "1.0.0"
REPO = "PrimeSyntaxTiktok/zelyvaro_audio_live"
APP = "ZELYVARO Audio Live"
BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))

class AudioThread(QThread):
    spectrum = Signal(list)
    error = Signal(str)
    def run(self):
        try:
            import soundcard as sc
            speaker = sc.default_speaker()
            if speaker is None:
                raise RuntimeError("Aucune sortie audio Windows par défaut.")
            mic = sc.get_microphone(id=str(speaker.id), include_loopback=True)
            if mic is None:
                raise RuntimeError("WASAPI loopback indisponible.")
            n = 2048
            with mic.recorder(samplerate=48000, blocksize=n) as rec:
                while not self.isInterruptionRequested():
                    block = np.asarray(rec.record(numframes=n), dtype=np.float32)
                    mono = block.mean(axis=1) if block.ndim == 2 else block
                    if len(mono) != n:
                        mono = np.resize(mono, n)
                    fft = np.abs(np.fft.rfft(mono * np.hanning(n)))
                    bins = np.array_split(fft[1:900], 72)
                    values = [min(255, int(np.sqrt(max(0, x.mean()) * 12) * 255)) for x in bins]
                    self.spectrum.emit(values)
        except Exception as exc:
            self.error.emit(str(exc))

class Window(QMainWindow):
    update_found = Signal(str, str)
    message = Signal(str)
    downloaded = Signal(str)
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP + " " + VERSION)
        self.resize(450, 800)
        self.setMinimumSize(270, 480)
        self.view = QWebEngineView()
        self.setCentralWidget(self.view)
        self.view.load(QUrl.fromLocalFile(str(BASE / "wallpaper.html")))
        self.ready = False
        self.pending = None
        self.view.loadFinished.connect(self.loaded)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.flush)
        self.timer.start(35)
        self.menuBar().addAction("Relancer capture audio", self.start_audio)
        self.menuBar().addAction("Vérifier les mises à jour", lambda: self.check_updates(False))
        self.menuBar().addAction("Masquer / afficher le panneau", lambda: self.view.page().runJavaScript("document.body.classList.toggle('clean')"))
        self.update_found.connect(self.confirm_update)
        self.message.connect(lambda s: QMessageBox.information(self, APP, s))
        self.downloaded.connect(self.launch_installer)
        self.audio = None
        self.start_audio()
        QTimer.singleShot(3000, lambda: self.check_updates(True))
    def loaded(self, ok):
        self.ready = ok
    def start_audio(self):
        if self.audio:
            self.audio.requestInterruption()
            self.audio.wait(1800)
            if self.audio.isRunning():
                QMessageBox.warning(self, APP, "Capture encore active.")
                return
        self.audio = AudioThread(self)
        self.audio.spectrum.connect(self.receive)
        self.audio.error.connect(lambda x: QMessageBox.warning(self, "Capture audio", x))
        self.audio.start()
    def receive(self, values):
        self.pending = values
    def flush(self):
        if self.ready and self.pending is not None:
            values = self.pending
            self.pending = None
            self.view.page().runJavaScript("window.setDesktopAudio(" + json.dumps(values) + ")")
    def check_updates(self, silent):
        def worker():
            try:
                req = urllib.request.Request("https://api.github.com/repos/" + REPO + "/releases/latest", headers={"User-Agent": APP})
                with urllib.request.urlopen(req, timeout=12) as res:
                    item = json.load(res)
                tag = item["tag_name"].lstrip("v")
                asset = next((a for a in item.get("assets", []) if a["name"].endswith("-setup.exe")), None)
                if Version(tag) > Version(VERSION) and asset:
                    self.update_found.emit(tag, asset["browser_download_url"])
                elif not silent:
                    self.message.emit("Vous utilisez la dernière version publiée.")
            except Exception as exc:
                if not silent:
                    self.message.emit("Impossible de vérifier les mises à jour : " + str(exc))
        threading.Thread(target=worker, daemon=True).start()
    def confirm_update(self, tag, url):
        if QMessageBox.question(self, APP, "Installer la mise à jour " + tag + " depuis GitHub ?") != QMessageBox.StandardButton.Yes:
            return
        def worker():
            try:
                path = Path(tempfile.gettempdir()) / ("ZelyvaroAudioLive-" + tag + "-setup.exe")
                req = urllib.request.Request(url, headers={"User-Agent": APP})
                with urllib.request.urlopen(req, timeout=120) as response, path.open("wb") as f:
                    import shutil
                    shutil.copyfileobj(response, f)
                self.downloaded.emit(str(path))
            except Exception as exc:
                self.message.emit("Téléchargement échoué : " + str(exc))
        threading.Thread(target=worker, daemon=True).start()
    def launch_installer(self, path):
        subprocess.Popen([path, "/CLOSEAPPLICATIONS"])
        QApplication.quit()
    def closeEvent(self, event):
        if self.audio:
            self.audio.requestInterruption()
            self.audio.wait(1500)
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec())
