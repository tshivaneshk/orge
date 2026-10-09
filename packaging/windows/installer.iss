; Inno Setup Script for ORGE
; Creates a professional Windows installer: ORGE-Setup-2.2.0.exe

#define MyAppName "ORGE"
#define MyAppVersion "2.2.0"
#define MyAppPublisher "ORGE Contributors"
#define MyAppURL "https://github.com/tshivaneshk/orge"
#define MyAppExeName "ORGE.exe"
#define MyCliExeName "orge.exe"

[Setup]
AppId={{9F8264D4-B83A-4217-A186-0D3B0E8FA2C1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\..\LICENSE
OutputDir=..\..\dist-installer
OutputBaseFilename=ORGE-Setup-{#MyAppVersion}
SetupIconFile=app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ChangesEnvironment=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "addtopath"; Description: "Add ORGE CLI to user/system PATH environment variable"; GroupDescription: "System Integration:"

[Files]
Source: "..\..\dist\ORGE\ORGE.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\dist\ORGE\orge-cli.exe"; DestDir: "{app}"; DestName: "orge-cli.exe"; Flags: ignoreversion
Source: "..\..\dist\orge.exe"; DestDir: "{app}\bin"; DestName: "orge.exe"; Flags: ignoreversion
Source: "..\..\dist\ORGE\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "ORGE.exe,orge.exe,orge-cli.exe"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Registry]
; If elevated to admin, update System PATH (HKLM) with {app}\bin
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; \
    ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}\bin;{app}"; \
    Tasks: addtopath; Check: IsAdminInstallMode and NeedsAddPathHKLM(ExpandConstant('{app}\bin'))

; If installed as regular user, update User PATH (HKCU) with {app}\bin
Root: HKCU; Subkey: "Environment"; \
    ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}\bin;{app}"; \
    Tasks: addtopath; Check: (not IsAdminInstallMode) and NeedsAddPathHKCU(ExpandConstant('{app}\bin'))

[Code]
function NeedsAddPathHKLM(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_LOCAL_MACHINE,
    'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
    'Path', OrigPath)
  then begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + Param + ';', ';' + OrigPath + ';') = 0;
end;

function NeedsAddPathHKCU(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER,
    'Environment',
    'Path', OrigPath)
  then begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + Param + ';', ';' + OrigPath + ';') = 0;
end;
