; Instalador de Peripheral Battery (Inno Setup 6). Lo compila build.ps1:
;   ISCC.exe /DAppVersion=1.0.0 installer.iss

#define AppName "Peripheral Battery"
#define AppExe "PeripheralBattery.exe"
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{6F3B2A41-8C7E-4D52-9B1A-3E5C7D9F2A10}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Marco
; Instalacion por usuario: no pide administrador, asi las actualizaciones son silenciosas.
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\PeripheralBattery
DisableDirPage=yes
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=PeripheralBattery-{#AppVersion}-setup
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Si la app sigue abierta al actualizar, el instalador la cierra.
CloseApplications=force
RestartApplications=no

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "autostart"; Description: "Iniciar con Windows"

[InstallDelete]
; Limpia librerias de la version anterior antes de copiar las nuevas.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "dist\PeripheralBattery\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"

[Registry]
; El autoarranque tambien se cambia desde el menu de la app, asi que solo lo toca la
; instalacion interactiva: las actualizaciones (silenciosas) respetan lo que eligio el usuario.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "PeripheralBattery"; ValueData: """{app}\{#AppExe}"""; Tasks: autostart; Check: not WizardSilent
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "PeripheralBattery"; Flags: deletevalue; Tasks: not autostart; Check: not WizardSilent
; Siempre registrar el borrado al desinstalar, aunque se haya activado desde la app.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "PeripheralBattery"; Flags: uninsdeletevalue

[Run]
; Instalacion normal: casilla "Iniciar" al final. Actualizacion silenciosa: se relanza sola.
Filename: "{app}\{#AppExe}"; Description: "Iniciar {#AppName}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\{#AppExe}"; Flags: nowait skipifnotsilent

[UninstallDelete]
; Datos de la app: log, ajustes y estadisticas de bateria.
Type: filesandordirs; Name: "{localappdata}\PeripheralBattery"

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM {#AppExe}"; Flags: runhidden; RunOnceId: "KillApp"
