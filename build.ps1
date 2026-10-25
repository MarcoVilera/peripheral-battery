# Compila la app y genera el instalador en dist\PeripheralBattery-<version>-setup.exe
#   .\build.ps1            build
#   .\build.ps1 -Release   build + publica un release en GitHub (requiere gh logueado)
param([switch]$Release)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$version = (Select-String -Path version.py -Pattern '^VERSION = "(.+)"').Matches[0].Groups[1].Value
Write-Host "== Peripheral Battery $version =="

python icons.py | Out-Null

python -m PyInstaller --noconfirm --clean --windowed --onedir `
    --name PeripheralBattery --icon assets\icon.ico `
    --distpath dist --workpath build app.py
if ($LASTEXITCODE) { throw "PyInstaller fallo" }

$iscc = @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "No se encontro Inno Setup 6 (winget install JRSoftware.InnoSetup)" }
& $iscc /Q "/DAppVersion=$version" installer.iss
if ($LASTEXITCODE) { throw "Inno Setup fallo" }

$setup = "dist\PeripheralBattery-$version-setup.exe"
Write-Host "Instalador: $setup"

if ($Release) {
    gh release create "v$version" $setup --title "v$version" --generate-notes
    if ($LASTEXITCODE) { throw "gh release fallo" }
}
