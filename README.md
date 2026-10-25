# Peripheral Battery

App de bandeja para Windows que muestra la batería de mouses, teclados y otros
periféricos inalámbricos que no la exponen a Windows. Muestra un icono por dispositivo
conectado, con el porcentaje y un color según el nivel (azul si está cargando).

## Dispositivos soportados

| Dispositivo | Conexión | Driver |
|---|---|---|
| Fantech KANATA WIRELESS WG9RD | dongle 2.4GHz / cable USB | `devices/fantech_wg9rd.py` |

## Agregar un dispositivo

1. Crear `devices/<modelo>.py` con una subclase de `Driver` (ver `devices/base.py`).
   `read()` devuelve `Status(pct, charging, connection)`, `None` si no está conectado,
   o lanza `DeviceError` si está conectado pero no responde.
2. Registrarla en `DRIVERS` en `devices/__init__.py`.
3. Probar con `python battery.py`.

Para descubrir el protocolo de un dispositivo nuevo, lo más rápido suele ser revisar el
software oficial del fabricante (muchos son apps Electron con el JS sin compilar).

## Desarrollo

```powershell
pip install hidapi pystray pillow pyinstaller
python battery.py   # lectura por consola
python app.py       # app de bandeja
```

## Build e instalador

Requiere Inno Setup 6 (`winget install JRSoftware.InnoSetup`).

```powershell
.\build.ps1           # genera dist\PeripheralBattery-<version>-setup.exe
.\build.ps1 -Release  # además publica el release en GitHub (requiere gh)
```

## Actualizaciones

La app revisa GitHub Releases al iniciar y cada 6 horas (`GITHUB_REPO` en `version.py`).
Si hay una versión mayor, descarga el instalador y lo corre en modo silencioso; el
instalador cierra la app, reemplaza los archivos y la vuelve a abrir.

Para publicar una versión nueva: subir `VERSION` en `version.py` y correr `.\build.ps1 -Release`.

Logs: `%LOCALAPPDATA%\PeripheralBattery\app.log`.
