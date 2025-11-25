;  Architects Tool No.1 - Inno Setup Script

#define MyAppName "Architects Tool No.1"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Platinum Zenith"
#define MyAppExeName "ArchitectsToolNo1.exe"

[Setup]
; Application info
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=installer_output
OutputBaseFilename=ArchitectsToolNo1_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

; Icon
SetupIconFile=assets\icon.ico

; License (optional - uncomment if you have a license file)
; LicenseFile=LICENSE.txt

; Privileges
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "Start automatically with Windows"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
Source: "dist\ArchitectsToolNo1.exe"; DestDir: "{app}"; Flags: ignoreversion
; Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{autostartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// Custom installation messages
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
