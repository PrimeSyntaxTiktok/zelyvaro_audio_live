"""ctypes binding for Windows application-output loopback (no microphone)."""
import ctypes as ct
import os
from pathlib import Path
import sys

import numpy as np


class AppInfo(ct.Structure):
    _fields_ = [('pid', ct.c_uint32), ('active', ct.c_uint32), ('created', ct.c_uint64),
                ('path', ct.c_wchar * 1024), ('name', ct.c_wchar * 260)]


_library = None


def supported():
    return sys.platform == 'win32' and sys.getwindowsversion().build >= 20348


def library():
    global _library
    if _library is None:
        root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
        path = root / 'zelyvaro_capture.dll'
        if not path.is_file() and not getattr(sys, 'frozen', False):
            path = root.parent / 'build/native/zelyvaro_capture.dll'
        lib = ct.CDLL(str(path))
        lib.zal_list_apps.argtypes = [ct.POINTER(AppInfo), ct.c_uint, ct.POINTER(ct.c_uint)]
        lib.zal_list_apps.restype = ct.c_long
        lib.zal_capture_create.argtypes = [ct.c_uint32, ct.c_uint64, ct.POINTER(ct.c_long)]
        lib.zal_capture_create.restype = ct.c_void_p
        lib.zal_capture_read.argtypes = [ct.c_void_p, ct.POINTER(ct.c_int16), ct.c_uint,
                                        ct.POINTER(ct.c_uint), ct.c_uint32]
        lib.zal_capture_read.restype = ct.c_long
        lib.zal_capture_destroy.argtypes = [ct.c_void_p]
        lib.zal_capture_destroy.restype = None
        _library = lib
    return _library


def check(hr, action):
    if hr < 0:
        if hr & 0xffffffff == 0x8007042b:
            raise RuntimeError('L’application choisie est fermée ou a redémarré.')
        raise OSError(f'{action} (Windows 0x{hr & 0xffffffff:08X})')


def applications():
    """Apps with active or paused playback sessions, grouped by process tree."""
    if not supported():
        return []
    items = (AppInfo * 1024)()
    count = ct.c_uint()
    check(library().zal_list_apps(items, len(items), ct.byref(count)), 'Liste des applications audio indisponible')
    result = [{'mode': 'application', 'pid': int(item.pid), 'created': int(item.created),
               'path': item.path, 'name': item.name, 'active': bool(item.active)}
              for item in items[:count.value] if item.created and item.pid != os.getpid()]
    return sorted(result, key=lambda item: (not item['active'], item['name'].casefold(), item['pid']))


def resolve_source(saved, available):
    """Reconnect by executable after restart, never by an unverified reused PID."""
    if saved.get('mode') != 'application':
        return {'mode': 'system', 'name': 'Tout le son Windows'}
    matches = [item for item in available if item['path'].casefold() == saved.get('path', '').casefold()]
    for item in matches:
        if item['pid'] == saved.get('pid') and item['created'] == saved.get('created'):
            return item
    return matches[0] if matches else None


class ProcessCapture:
    def __init__(self, source):
        if not supported():
            raise RuntimeError('La capture par application nécessite Windows 11 (ou Windows build 20348 minimum).')
        self.lib = library()
        hr = ct.c_long()
        self.handle = self.lib.zal_capture_create(source['pid'], source['created'], ct.byref(hr))
        check(hr.value, 'Impossible d’ouvrir la capture de cette application')
        if not self.handle:
            raise RuntimeError('Windows n’a pas ouvert la capture de cette application.')
        self.buffer = (ct.c_int16 * (16384 * 2))()

    def read(self, timeout=80):
        count = ct.c_uint()
        check(self.lib.zal_capture_read(self.handle, self.buffer, 16384, ct.byref(count), timeout),
              'Capture de l’application interrompue')
        return np.ctypeslib.as_array(self.buffer)[:count.value * 2].reshape(-1, 2).astype(np.float32) / 32768

    def close(self):
        if self.handle:
            self.lib.zal_capture_destroy(self.handle)
            self.handle = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def media_info(application=''):
    lib = library()
    if not hasattr(lib, 'zal_media_info'):
        return {'artist': '', 'title': '', 'available': False}
    function = lib.zal_media_info
    function.argtypes = [ct.c_wchar_p, ct.c_wchar_p, ct.c_uint, ct.c_wchar_p, ct.c_uint]
    function.restype = ct.c_long
    artist, title = ct.create_unicode_buffer(512), ct.create_unicode_buffer(1024)
    result = function(application, artist, len(artist), title, len(title))
    return {'artist': artist.value, 'title': title.value, 'available': result == 0}
