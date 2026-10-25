# Compila la app y genera el instalador en dist\PeripheralBattery-<version>-setup.exe
#   .\build.ps1                    app + instalador
#   .\build.ps1 -Stage App         solo el ejecutable (dist\PeripheralBattery\)
#   .\build.ps1 -Stage Installer   solo el instalador, a partir de dist\PeripheralBattery\
#   .\build.ps1 -Release           build + publica el release en GitHub (requiere gh logueado)
# El CI (.github/workflows/build.yml) usa las etapas por separado para firmar el .exe
# antes de empaquetarlo en el instalador.
param(
    [ValidateSet('All', 'App', 'Installer')] [string]$Stage = 'All',
    [switch]$Release
)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$version = (Select-String -Path version.py -Pattern '^VERSION = "(.+)"').Matches[0].Groups[1].Value
Write-Host "== Peripheral Battery $version ($Stage) =="

if ($Stage -in 'All', 'App') {
    python icons.py | Out-Null
    New-Item -ItemType Directory -Force build | Out-Null
    python version_info.py build\version_info.txt
    python -m PyInstaller --noconfirm --clean --windowed --onedir `
        --name PeripheralBattery --icon assets\icon.ico `
        --version-file build\version_info.txt `
        --distpath dist --workpath build app.py
    if ($LASTEXITCODE) { throw "PyInstaller fallo" }
}

if ($Stage -in 'All', 'Installer') {
    if (-not (Test-Path assets\icon.ico)) { python icons.py | Out-Null }
    $iscc = @(
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $iscc -and $env:CI) {
        choco install innosetup -y --no-progress | Out-Null
        $iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    }
    if (-not $iscc) { throw "No se encontro Inno Setup 6 (winget install JRSoftware.InnoSetup)" }
    & $iscc /Q "/DAppVersion=$version" installer.iss
    if ($LASTEXITCODE) { throw "Inno Setup fallo" }
    $setup = "dist\PeripheralBattery-$version-setup.exe"
    Write-Host "Instalador: $setup"
}

if ($Release) {
    $gh = (Get-Command gh -EA SilentlyContinue).Source
    if (-not $gh) { $gh = "$env:LOCALAPPDATA\Microsoft\WinGet\Links\gh.exe" }
    & $gh release create "v$version" $setup --title "v$version" --generate-notes
    if ($LASTEXITCODE) { throw "gh release fallo" }
}
