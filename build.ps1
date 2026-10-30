param([string]$Python = 'python', [switch]$SkipDependencies)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not $SkipDependencies) {
    & $Python -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
}
& (Join-Path $PSScriptRoot 'tools/build-native.ps1')
& $Python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
& $Python tools/build.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }
Write-Host 'Application: dist/ZELYVARO Audio Live/'
