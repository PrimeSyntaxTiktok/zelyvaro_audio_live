#define AppName "ZELYVARO Audio Live"
#define AppVersion "1.0.0"
[Setup]
AppId={{576F3D66-B09B-45B5-B653-A5D6B8DD18DF}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\ZELYVARO Audio Live
DefaultGroupName=ZELYVARO
OutputDir=output
OutputBaseFilename=ZelyvaroAudioLive-1.0.0-setup
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
PrivilegesRequired=lowest
[Files]
Source: "dist\ZELYVARO Audio Live\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
[Icons]
Name: "{group}\ZELYVARO Audio Live"; Filename: "{app}\ZELYVARO Audio Live.exe"
Name: "{autodesktop}\ZELYVARO Audio Live"; Filename: "{app}\ZELYVARO Audio Live.exe"
[Run]
Filename: "{app}\ZELYVARO Audio Live.exe"; Description: "Lancer ZELYVARO Audio Live"; Flags: nowait postinstall skipifsilent
