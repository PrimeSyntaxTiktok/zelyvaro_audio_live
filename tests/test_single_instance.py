from pathlib import Path
import os
import subprocess
import sys
import tempfile
import time
import unittest

from PySide6.QtCore import QCoreApplication
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from single_instance import SingleInstance


class SingleInstanceTests(unittest.TestCase):
    def test_second_process_activates_owner_then_lock_is_released(self):
        app = QCoreApplication.instance() or QCoreApplication([])
        app.setApplicationName('ZelyvaroAudioLive')
        with tempfile.TemporaryDirectory() as folder:
            owner = SingleInstance(folder)
            self.assertTrue(owner.acquire())
            activations = []
            owner.bind(lambda: activations.append(True))
            script = ('from PySide6.QtCore import QCoreApplication;'
                      'from single_instance import SingleInstance;import sys;'
                      'app=QCoreApplication([]);app.setApplicationName("Other shortcut");gate=SingleInstance(sys.argv[1]);'
                      'result=gate.acquire();print(int(result));'
                      'gate.close() if result else None')
            env = os.environ.copy()
            env['PYTHONPATH'] = str(Path(__file__).resolve().parents[1] / 'app')
            child = subprocess.Popen([sys.executable, '-c', script, folder],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
            try:
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline and (child.poll() is None or not activations):
                    app.processEvents()
                    time.sleep(.01)
                stdout, stderr = child.communicate(timeout=2)
                self.assertEqual(child.returncode, 0, stderr.decode())
                self.assertEqual(stdout.strip(), b'0')
                self.assertEqual(activations, [True])
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait()
                owner.close()
            replacement = SingleInstance(folder)
            self.assertTrue(replacement.acquire())
            replacement.close()
