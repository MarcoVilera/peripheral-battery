# Peripheral Battery

App de bandeja para Windows que muestra la batería de mouses, teclados y otros
periféricos inalámbricos que no la exponen a Windows. Al hacer clic en el icono se abre
un panel estilo Windows 11 (sigue el tema claro/oscuro y el color de acento) con cada
dispositivo conectado: tipo, conexión, porcentaje, estado de carga y tiempo estimado.

- **Tiempo estimado:** el restante de batería y el que falta para completar la carga.
  Se aprende midiendo la velocidad de descarga/carga; aparece cuando hay datos suficientes.
- **Aviso de batería baja** con umbral configurable.
- **Iniciar con Windows** y **actualizaciones automáticas** desde GitHub Releases.

## Dispositivos soportados

| Dispositivo | Conexión | Driver |
|---|---|---|
| Fantech KANATA WIRELESS WG9RD | dongle 2.4GHz / cable USB | `devices/fantech_wg9rd.py` |

## Agregar un dispositivo

1. Crear `devices/<modelo>.py` con una subclase de `Driver` (ver `devices/base.py`).
   `read()` devuelve `Status(pct, charging, connection)`, `None` si no está conectado,
   o lanza `DeviceError` si está conectado pero no responde. `kind` define el icono del
   panel: `mouse`, `keyboard`, `headset`, `gamepad` u `other`.
2. Registrarla en `DRIVERS` en `devices/__init__.py`.
3. Probar con `python battery.py`.

Para descubrir el protocolo de un dispositivo nuevo, lo más rápido suele ser revisar el
software oficial del fabricante (muchos son apps Electron con el JS sin compilar).

## Desarrollo

```powershell
pip install hidapi PySide6-Essentials pillow pyinstaller
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

## Datos

En `%LOCALAPPDATA%\PeripheralBattery` (se borra al desinstalar):

- `app.log`: log con rotación, como máximo ~512 KB.
- `settings.json`: opciones del panel.
- `battery_stats.json`: velocidades de carga/descarga aprendidas.

Los instaladores descargados por las actualizaciones se borran de `%TEMP%` al iniciar.
