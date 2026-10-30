"""Freeze Windows app with version metadata and dependency license texts."""
from pathlib import Path
import importlib.metadata as metadata
import shutil
import sys
import PyInstaller.__main__
from PyInstaller.utils.win32.versioninfo import (
    VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
from version import VERSION, APP
build = ROOT / 'build'
build.mkdir(exist_ok=True)
numbers = tuple(map(int, VERSION.split('.'))) + (0,)
info = VSVersionInfo(ffi=FixedFileInfo(filevers=numbers, prodvers=numbers, fileType=1), kids=[
    StringFileInfo([StringTable('040904B0', [
        StringStruct('CompanyName', 'ZELYVARO'), StringStruct('FileDescription', APP),
        StringStruct('FileVersion', VERSION), StringStruct('ProductName', APP),
        StringStruct('ProductVersion', VERSION), StringStruct('OriginalFilename', APP + '.exe')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])])
version_file = build / 'version-info.txt'
version_file.write_text(str(info), encoding='utf8')
licenses = build / 'licenses'
licenses.mkdir(exist_ok=True)
for package in ('PySide6', 'PySide6-Addons', 'PySide6-Essentials', 'shiboken6', 'numpy', 'PyAudioWPatch', 'packaging'):
    dist = metadata.distribution(package)
    for file in dist.files or []:
        if any(word in str(file).lower() for word in ('license', 'copying', 'notice')):
            source = Path(dist.locate_file(file))
            if source.is_file():
                target = licenses / package / str(file).replace('../', '')
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
PyInstaller.__main__.run(['--noconfirm', '--clean', '--onedir', '--windowed', '--name', APP,
    '--version-file', str(version_file), '--add-data', 'app/wallpaper.html;.',
    '--add-data', 'app/themes.js;.',
    '--add-binary', 'build/native/zelyvaro_capture.dll;.',
    '--add-data', str(licenses) + ';licenses', '--collect-all', 'pyaudiowpatch', 'app/main.py'])
