param([switch]$BuildTestPlayer)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$installation = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $installation) { throw 'MSVC x64 build tools are required' }
$devcmd = Join-Path $installation 'Common7/Tools/VsDevCmd.bat'
$nativeBuild = Join-Path $root 'build/native'
New-Item -ItemType Directory -Path $nativeBuild -Force | Out-Null
$lines = @('@echo off', ('call "' + $devcmd + '" -arch=x64 -host_arch=x64 >nul'), 'if errorlevel 1 exit /b 1', ('cd /d "' + $root + '"'), 'cl /nologo /std:c++20 /EHsc /W4 /O2 /MT /LD /DUNICODE /D_UNICODE /D_WIN32_WINNT=0x0A00 /Fo"build/native/process_loopback.obj" /Fe"build/native/zelyvaro_capture.dll" native/process_loopback.cpp /link /INCREMENTAL:NO /IMPLIB:"build/native/zelyvaro_capture.lib" ole32.lib mmdevapi.lib uuid.lib windowsapp.lib', 'if errorlevel 1 exit /b 1')
if ($BuildTestPlayer) {
    $lines += 'cl /nologo /std:c++17 /EHsc /W4 /O2 /MT /DUNICODE /D_UNICODE /Fo"build/native/tone_player.obj" /Fe"build/native/tone_player.exe" tests/tone_player.cpp /link /INCREMENTAL:NO winmm.lib'
    $lines += 'if errorlevel 1 exit /b 1'
}
$lines += 'exit /b 0'
$script = Join-Path $nativeBuild 'compile.cmd'
[System.IO.File]::WriteAllLines($script, $lines, [System.Text.Encoding]::Default)
& cmd.exe /d /c $script
if ($LASTEXITCODE -ne 0) { throw 'Native audio bridge compilation failed' }
