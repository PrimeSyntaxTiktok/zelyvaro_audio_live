#define AppName "ZELYVARO Audio Live"
#ifndef AppVersion
  #define AppVersion "1.3.1"
#endif
[Setup]
AppId={{576F3D66-B09B-45B5-B653-A5D6B8DD18DF}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=ZELYVARO
AppPublisherURL=https://github.com/PrimeSyntaxTiktok/zelyvaro_audio_live
DefaultDirName={localappdata}\Programs\ZELYVARO Audio Live
DefaultGroupName=ZELYVARO
OutputDir=output
OutputBaseFilename=ZelyvaroAudioLive-{#AppVersion}-setup
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
CloseApplications=yes
RestartApplications=yes
PrivilegesRequired=lowest
WizardStyle=modern
SetupIconFile=app\app.ico
UninstallDisplayIcon={app}\ZELYVARO Audio Live.exe
SetupLogging=yes
[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; GroupDescription: "Raccourcis :"
[Files]
Source: "dist\ZELYVARO Audio Live\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
[Icons]
Name: "{group}\ZELYVARO Audio Live"; Filename: "{app}\ZELYVARO Audio Live.exe"; AppUserModelID: "ZELYVARO.AudioLive"
Name: "{autodesktop}\ZELYVARO Audio Live"; Filename: "{app}\ZELYVARO Audio Live.exe"; Tasks: desktopicon; AppUserModelID: "ZELYVARO.AudioLive"
[Run]
Filename: "{app}\ZELYVARO Audio Live.exe"; Description: "Lancer ZELYVARO Audio Live"; Flags: nowait postinstall skipifsilent
Filename: "{app}\ZELYVARO Audio Live.exe"; Flags: nowait; Check: IsUpdate
[Code]
function IsUpdate: Boolean;
begin
  Result := ExpandConstant('{param:UPDATE|0}') = '1';
end;
