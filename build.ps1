$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
py -3.11 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\pyinstaller.exe --noconfirm --clean --onedir --windowed --name "ZELYVARO Audio Live" --add-data "app/wallpaper.html;." --collect-all soundcard --collect-all PySide6 app/main.py
Write-Host "Executable dans dist/ZELYVARO Audio Live/"
