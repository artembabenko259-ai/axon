; AXON Inno Setup — Core.AXON Windows installer
; Built automatically by build.bat (PyInstaller + ISCC)

#define MyAppName "AXON"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "AXON Core Team"
#define MyAppExeName "axon.exe"
#define MyAppId "{{A7F3E2B1-4C8D-4E9A-9F1B-2D8E6C5A4F30}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\AXON
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist\setup
OutputBaseFilename=AXON_Setup_v{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
ChangesEnvironment=yes
; Winget silent install (/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-)
DisableWelcomePage=no
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\exe\axon\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\build\bundle-staging\.axon\*"; DestDir: "{app}\.axon"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\build\bundle-staging\zenith-web\*"; DestDir: "{app}\zenith-web"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\build\bundle-staging\node\*"; DestDir: "{app}\node"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
const
  EnvironmentKey = 'Environment';

function SendMessageTimeout(hWnd: HWND; Msg: UINT; wParam: LongWord; lParam: String; fuFlags: UINT; uTimeout: UINT; var lpdwResult: LongWord): LongInt; external 'SendMessageTimeoutW@user32.dll stdcall';

procedure EnvBroadcastChange;
var
  SendResult: LongWord;
begin
  SendMessageTimeout($FFFF, $001A, 0, 'Environment', 2, 5000, SendResult);
end;

procedure EnvAddPath(InstallPath: string);
var
  Paths: string;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, EnvironmentKey, 'Path', Paths) then
    Paths := '';
  if Pos(';' + Uppercase(InstallPath) + ';', ';' + Uppercase(Paths) + ';') = 0 then
  begin
    if Paths = '' then
      Paths := InstallPath
    else
      Paths := Paths + ';' + InstallPath;
    if not RegWriteExpandStringValue(HKEY_CURRENT_USER, EnvironmentKey, 'Path', Paths) then
      RegWriteStringValue(HKEY_CURRENT_USER, EnvironmentKey, 'Path', Paths);
    EnvBroadcastChange;
  end;
end;

procedure EnvRemovePath(InstallPath: string);
var
  Paths: string;
begin
  if RegQueryStringValue(HKEY_CURRENT_USER, EnvironmentKey, 'Path', Paths) then
  begin
    StringChangeEx(Paths, ';' + InstallPath, '', True);
    StringChangeEx(Paths, InstallPath + ';', '', True);
    StringChangeEx(Paths, InstallPath, '', True);
    if not RegWriteExpandStringValue(HKEY_CURRENT_USER, EnvironmentKey, 'Path', Paths) then
      RegWriteStringValue(HKEY_CURRENT_USER, EnvironmentKey, 'Path', Paths);
    EnvBroadcastChange;
  end;
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    EnvAddPath(ExpandConstant('{app}'));
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    EnvRemovePath(ExpandConstant('{app}'));
end;

[UninstallDelete]
Type: filesandordirs; Name: "{app}\.axon"
Type: filesandordirs; Name: "{app}\zenith-web"
Type: filesandordirs; Name: "{app}\node"
