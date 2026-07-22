; ============================================================
; HP Semiconductor Analyzer Controller -- Inno Setup 6 script
;
; Creates a self-installing Windows EXE that:
;   - Installs to  %ProgramFiles%\HP Semiconductor Analyzer\
;   - Adds a Start Menu group with launch + uninstall shortcuts
;   - Optionally creates a Desktop shortcut
;   - Registers an Add/Remove Programs entry with uninstaller
;
; PREREQUISITES
;   1. Run  build_exe.ps1  (or build_exe.bat) first so that
;      dist\HP_Analyzer\  is populated.
;   2. Install Inno Setup 6 from  https://jrsoftware.org/isdl.php
;   3. Either:
;        a. Open this file in the Inno Setup IDE -> press F9
;        b. Run from PowerShell:
;             & "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
;        c. Run build_exe.ps1 -Installer (auto-detects ISCC.exe)
;
; OUTPUT
;   release\HP_Analyzer_v{AppVersion}_Setup.exe
;   (~120-200 MB self-extracting installer, no Python or VISA needed)
;
; NOTE ON VISA DRIVERS
;   The installer bundles pyvisa-py but NOT NI-VISA or Keysight IO Libraries.
;   Users who connect via GPIB must install one separately:
;     - NI-VISA       https://www.ni.com/visa
;     - Keysight IO   https://www.keysight.com/find/iosuite
;   USB-TMC and LAN instruments work out of the box via pyvisa-py.
; ============================================================

#define AppName        "HP Semiconductor Analyzer"
#define AppVersion     "1.1.0"
#define AppPublisher   "Prashant Srinivasan"
#define AppURL         "https://github.com/prashantUCSB/hp-semiconductor-analyzer"
#define AppExeName     "HP_Analyzer.exe"
#define AppDistFolder  "dist\HP_Analyzer"

[Setup]
; Unique GUID -- do NOT reuse the Keithley installer GUID
AppId={{C4E7A2F1-8B3D-4E9C-A6F2-3B5D7E1C4A8F}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} v{#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases

; Install location
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}

; Output
OutputDir=release
OutputBaseFilename=HP_Analyzer_v{#AppVersion}_Setup

; Compression -- lzma2 ultra cuts size by ~40-50%
Compression=lzma2/ultra64
SolidCompression=yes

; Wizard appearance
WizardStyle=modern
DisableProgramGroupPage=yes
DisableWelcomePage=no

; Require 64-bit Windows 10 1903+ (required for consistent Qt5 DPI behavior)
MinVersion=10.0.18362
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Need admin rights to write under %ProgramFiles%
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=commandline

; Uninstaller metadata
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExeName}

; Add/Remove Programs metadata
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Setup
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; \
  Description: "{cm:CreateDesktopIcon}"; \
  GroupDescription: "{cm:AdditionalIcons}"; \
  Flags: unchecked

[Files]
; Main executable
Source: "{#AppDistFolder}\{#AppExeName}"; \
  DestDir: "{app}"; \
  Flags: ignoreversion

; PyInstaller 6+ _internal bundle (Qt DLLs, Python stdlib, instrument drivers)
; PyInstaller 6 places all support files in _internal\ -- handled recursively here.
Source: "{#AppDistFolder}\_internal\*"; \
  DestDir: "{app}\_internal"; \
  Flags: ignoreversion recursesubdirs createallsubdirs

; Fallback: PyInstaller 5 flat layout (files alongside the EXE)
; Inno Setup silently skips globs matching zero files, so safe to keep.
Source: "{#AppDistFolder}\*.dll"; \
  DestDir: "{app}"; \
  Flags: ignoreversion skipifsourcedoesntexist
Source: "{#AppDistFolder}\*.pyd"; \
  DestDir: "{app}"; \
  Flags: ignoreversion skipifsourcedoesntexist
Source: "{#AppDistFolder}\*.manifest"; \
  DestDir: "{app}"; \
  Flags: ignoreversion skipifsourcedoesntexist
Source: "{#AppDistFolder}\config\*"; \
  DestDir: "{app}\config"; \
  Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

[Icons]
; Start Menu shortcuts
Name: "{group}\{#AppName}";             Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}";  Filename: "{uninstallexe}"

; Desktop shortcut (optional -- user must tick the box)
Name: "{commondesktop}\{#AppName}"; \
  Filename: "{app}\{#AppExeName}"; \
  Tasks: desktopicon

[Run]
; Offer to launch immediately after installation
Filename: "{app}\{#AppExeName}"; \
  Description: "{cm:LaunchProgram,{#AppName}}"; \
  Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove user-generated exports folder if present
Type: filesandordirs; Name: "{app}\exports"

[Code]
// Post-install: warn if no VISA runtime is detected
procedure CurStepChanged(CurStep: TSetupStep);
var
  NIFound, KSFound: Boolean;
begin
  if CurStep = ssPostInstall then
  begin
    NIFound := RegKeyExists(HKLM, 'SOFTWARE\National Instruments\NI-VISA');
    KSFound := RegKeyExists(HKLM, 'SOFTWARE\Keysight\IO Libraries Suite');
    if (not NIFound) and (not KSFound) then
    begin
      MsgBox(
        'Installation complete!' + #13#10#13#10 +
        'GPIB adapter note:' + #13#10 +
        'To use a GPIB adapter (Keysight 82351B or NI USB-GPIB) you need' + #13#10 +
        'a VISA runtime installed separately:' + #13#10#13#10 +
        '  NI-VISA:      https://www.ni.com/visa' + #13#10 +
        '  Keysight IO:  https://www.keysight.com/find/iosuite' + #13#10#13#10 +
        'USB-TMC and LAN instruments work without a VISA runtime.',
        mbInformation, MB_OK
      );
    end;
  end;
end;
