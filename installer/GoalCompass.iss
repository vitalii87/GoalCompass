#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef NumericVersion
  #define NumericVersion "0.0.0"
#endif

#define AppName "GoalCompass"
#define AppPublisher "GoalCompass"
#define AppExeName "GoalCompass.exe"

[Setup]
AppId={{A84F56E4-6F88-45BC-93C6-5AA1DBB1104B}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\artifacts
OutputBaseFilename=GoalCompass-Setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
UninstallDisplayIcon={app}\{#AppExeName}
VersionInfoVersion={#NumericVersion}.0
VersionInfoCompany={#AppPublisher}
VersionInfoDescription=GoalCompass Windows Installer
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "ukrainian"; MessagesFile: "compiler:Languages\Ukrainian.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\GoalCompass\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{app}\data"; Flags: uninsneveruninstall
Name: "{app}\data\runtime"; Flags: uninsneveruninstall
Name: "{app}\data\user_config"; Flags: uninsneveruninstall

[Icons]
Name: "{group}\GoalCompass"; Filename: "{app}\{#AppExeName}"
Name: "{group}\GoalCompass Control Center"; Filename: "{app}\{#AppExeName}"; Parameters: "--component control-panel"
Name: "{group}\Check for GoalCompass Updates"; Filename: "{app}\{#AppExeName}"; Parameters: "--component updates"
Name: "{group}\Uninstall GoalCompass"; Filename: "{uninstallexe}"
Name: "{autodesktop}\GoalCompass"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch GoalCompass"; Flags: nowait postinstall skipifsilent
