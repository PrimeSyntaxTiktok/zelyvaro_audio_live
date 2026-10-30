"""Per-user lock and local activation channel, independent of installation path."""
import hashlib
import os
from pathlib import Path
import sys

from PySide6.QtCore import QLockFile
from PySide6.QtNetwork import QLocalServer, QLocalSocket


class SingleInstance:
    def __init__(self, profile):
        profile = Path(profile).resolve()
        profile.mkdir(parents=True, exist_ok=True)
        identity = hashlib.sha256(os.path.normcase(str(profile)).encode('utf8')).hexdigest()[:24]
        self.name = 'ZelyvaroAudioLive-' + identity
        self.lock = QLockFile(str(profile / 'application.lock'))
        self.lock.setStaleLockTime(0)
        self.server = None
        self.activate = None
        self.pending = False

    def acquire(self):
        if not self.lock.tryLock(0):
            # The first process may still be loading Qt. Keep its lock authoritative.
            for _ in range(12):
                client = QLocalSocket()
                client.connectToServer(self.name)
                if client.waitForConnected(250):
                    client.write(b'show\n')
                    client.waitForBytesWritten(250)
                    client.disconnectFromServer()
                    break
                from PySide6.QtCore import QThread
                QThread.msleep(100)
            return False
        self.server = QLocalServer()
        self.server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        QLocalServer.removeServer(self.name)
        if not self.server.listen(self.name):
            self.lock.unlock()
            raise RuntimeError('Impossible de créer le canal local de ZELYVARO.')
        self.server.newConnection.connect(self._connection)
        return True

    def bind(self, callback):
        self.activate = callback
        if self.pending:
            self.pending = False
            callback()

    def _connection(self):
        while self.server.hasPendingConnections():
            connection = self.server.nextPendingConnection()
            connection.disconnected.connect(connection.deleteLater)
            connection.disconnectFromServer()
            if self.activate:
                self.activate()
            else:
                self.pending = True

    def close(self):
        if self.server:
            self.server.close()
            self.server = None
        self.lock.unlock()


def activate_legacy_instance():
    """Bridge upgrades from 1.2.0, which had no lock/activation channel.

    Only the frozen Windows app needs this check. Show the existing main window
    in this Windows session and exit before creating another renderer or tray icon.
    """
    if sys.platform != 'win32' or not getattr(sys, 'frozen', False):
        return False
    import ctypes as C
    from ctypes import wintypes as W

    class Entry(C.Structure):
        _fields_ = [('dwSize', W.DWORD), ('cntUsage', W.DWORD), ('pid', W.DWORD),
                    ('heap', C.c_size_t), ('module', W.DWORD), ('threads', W.DWORD),
                    ('parent', W.DWORD), ('priority', W.LONG), ('flags', W.DWORD),
                    ('filename', W.WCHAR * 260)]
    kernel = C.WinDLL('kernel32', use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [W.DWORD, W.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = W.HANDLE
    kernel.Process32FirstW.argtypes = [W.HANDLE, C.POINTER(Entry)]
    kernel.Process32NextW.argtypes = [W.HANDLE, C.POINTER(Entry)]
    kernel.CloseHandle.argtypes = [W.HANDLE]
    kernel.ProcessIdToSessionId.argtypes = [W.DWORD, C.POINTER(W.DWORD)]
    session = W.DWORD()
    kernel.ProcessIdToSessionId(os.getpid(), C.byref(session))
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
    if snapshot == W.HANDLE(-1).value:
        return False
    pids = set()
    try:
        entry = Entry()
        entry.dwSize = C.sizeof(entry)
        available = kernel.Process32FirstW(snapshot, C.byref(entry))
        while available:
            other_session = W.DWORD()
            if (entry.pid != os.getpid() and entry.filename.casefold() == Path(sys.executable).name.casefold()
                    and kernel.ProcessIdToSessionId(entry.pid, C.byref(other_session))
                    and session.value == other_session.value):
                pids.add(entry.pid)
            available = kernel.Process32NextW(snapshot, C.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)
    if not pids:
        return False
    user = C.WinDLL('user32', use_last_error=True)
    callback_type = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
    user.EnumWindows.argtypes = [callback_type, W.LPARAM]
    user.GetWindowThreadProcessId.argtypes = [W.HWND, C.POINTER(W.DWORD)]
    user.GetWindowTextW.argtypes = [W.HWND, W.LPWSTR, C.c_int]
    user.ShowWindow.argtypes = [W.HWND, C.c_int]
    user.SetForegroundWindow.argtypes = [W.HWND]

    @callback_type
    def show(hwnd, _):
        pid = W.DWORD()
        user.GetWindowThreadProcessId(hwnd, C.byref(pid))
        if pid.value in pids:
            title = C.create_unicode_buffer(256)
            user.GetWindowTextW(hwnd, title, len(title))
            if title.value.startswith('ZELYVARO Audio Live'):
                user.ShowWindow(hwnd, 9)
                user.SetForegroundWindow(hwnd)
                return False
        return True
    user.EnumWindows(show, 0)
    return True
