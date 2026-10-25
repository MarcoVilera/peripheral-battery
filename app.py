"""Peripheral Battery: un icono en la bandeja por cada dispositivo conectado con su bateria."""
import ctypes
import logging
import os
import sys
import threading
import winreg
from pathlib import Path

import pystray

import icons
import updater
from devices import DRIVERS, DeviceError
from version import GITHUB_REPO, VERSION

APP_NAME = "Peripheral Battery"
POLL_S = 60
UPDATE_CHECK_S = 6 * 60 * 60
LOW_BATTERY = 15

LOG_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "PeripheralBattery"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=LOG_DIR / "app.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("app")


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "PeripheralBattery"  # mismo nombre que usa installer.iss


def autostart_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, RUN_VALUE)
        return True
    except OSError:
        return False


def set_autostart(enabled):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if enabled:
            winreg.SetValueEx(k, RUN_VALUE, 0, winreg.REG_SZ, f'"{sys.executable}"')
        else:
            try:
                winreg.DeleteValue(k, RUN_VALUE)
            except FileNotFoundError:
                pass


def single_instance():
    """Evita dos instancias a la vez (por ejemplo, al relanzarse tras una actualizacion)."""
    ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\PeripheralBatteryTray")
    return ctypes.windll.kernel32.GetLastError() != 183  # ERROR_ALREADY_EXISTS


class TrayIcon:
    """Un icono de bandeja con su propio hilo (pystray necesita un loop por icono)."""

    def __init__(self, app, key, text):
        self.text = text
        self.icon = pystray.Icon(key, icons.render(None), text[:127], menu=app.build_menu(self))
        threading.Thread(target=self.icon.run, args=(self._setup,), daemon=True).start()

    @staticmethod
    def _setup(icon):
        icon.visible = True

    def set(self, pct, charging, text):
        self.icon.icon = icons.render(pct, charging)
        self.icon.title = text[:127]
        if text != self.text:
            self.text = text
            self.icon.update_menu()

    def notify(self, msg):
        self.icon.notify(msg, APP_NAME)

    def stop(self):
        self.icon.stop()


class App:
    def __init__(self):
        self.stop_event = threading.Event()
        self.refresh_event = threading.Event()
        self.icons = {}  # driver.id -> TrayIcon
        self.placeholder = None  # icono gris cuando no hay ningun dispositivo
        self.low_warned = set()
        self.last_log = {}

    def build_menu(self, tray):
        return pystray.Menu(
            pystray.MenuItem(lambda _: tray.text, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Actualizar lectura", self.on_refresh, default=True),
            pystray.MenuItem(
                "Iniciar con Windows",
                self.on_toggle_autostart,
                checked=lambda _: autostart_enabled(),
                # Desde el codigo fuente sys.executable es python.exe: solo tiene sentido instalada.
                visible=getattr(sys, "frozen", False),
            ),
            pystray.MenuItem(
                "Buscar actualizaciones", self.on_check_updates, visible=bool(GITHUB_REPO)
            ),
            pystray.MenuItem(f"{APP_NAME} {VERSION}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Salir", self.on_quit),
        )

    def any_icon(self):
        return next(iter(self.icons.values()), self.placeholder)

    # --- lectura de baterias ---

    def poll_once(self):
        for drv in DRIVERS:
            try:
                st = drv.read()
            except DeviceError as e:
                self.show(drv, None, False, f"{drv.name}: {e}")
                continue
            except Exception as e:
                log.exception("Error leyendo %s", drv.id)
                self.show(drv, None, False, f"{drv.name}: error ({e})")
                continue
            if st is None:
                self.hide(drv)
                continue
            text = f"{drv.name}: {st.pct}%" + (" (cargando)" if st.charging else "")
            self.show(drv, st.pct, st.charging, text)
            self.check_low(drv, st.pct, st.charging)

        if self.icons and self.placeholder:
            self.placeholder.stop()
            self.placeholder = None
        elif not self.icons and not self.placeholder:
            self.placeholder = TrayIcon(self, "none", "Ningun dispositivo conectado")

    def show(self, drv, pct, charging, text):
        if self.last_log.get(drv.id) != text:
            log.info(text)
            self.last_log[drv.id] = text
        tray = self.icons.get(drv.id)
        if tray is None:
            tray = self.icons[drv.id] = TrayIcon(self, drv.id, text)
        tray.set(pct, charging, text)

    def hide(self, drv):
        tray = self.icons.pop(drv.id, None)
        if tray:
            log.info("%s desconectado", drv.name)
            self.last_log.pop(drv.id, None)
            tray.stop()

    def check_low(self, drv, pct, charging):
        if charging or pct > LOW_BATTERY + 5:
            self.low_warned.discard(drv.id)
        elif pct <= LOW_BATTERY and drv.id not in self.low_warned:
            self.low_warned.add(drv.id)
            self.icons[drv.id].notify(f"A {drv.name} le queda {pct}% de bateria.")

    # --- actualizaciones ---

    def update_loop(self):
        if not GITHUB_REPO:
            return
        # Primera revision al minuto de arrancar para no competir con el inicio de Windows.
        delay = 60
        while not self.stop_event.wait(delay):
            self.try_update(manual=False)
            delay = UPDATE_CHECK_S

    def try_update(self, manual):
        def notify(msg):
            if tray := self.any_icon():
                tray.notify(msg)

        try:
            found = updater.check()
        except Exception:
            log.exception("Error buscando actualizaciones")
            if manual:
                notify("No se pudo buscar actualizaciones.")
            return
        if not found:
            if manual:
                notify(f"Ya tienes la ultima version ({VERSION}).")
            return
        new_version, url = found
        log.info("Actualizando a %s desde %s", new_version, url)
        notify(f"Instalando la version {new_version}...")
        try:
            updater.download_and_install(url)
        except Exception:
            log.exception("Error instalando la actualizacion")
            notify("No se pudo instalar la actualizacion.")
            return
        self.on_quit()

    # --- menu ---

    def on_refresh(self, *_):
        self.refresh_event.set()

    def on_toggle_autostart(self, *_):
        enabled = not autostart_enabled()
        try:
            set_autostart(enabled)
            log.info("Iniciar con Windows: %s", enabled)
        except OSError:
            log.exception("No se pudo cambiar el inicio con Windows")
        for tray in [*self.icons.values(), self.placeholder]:
            if tray:
                tray.icon.update_menu()

    def on_check_updates(self, *_):
        threading.Thread(target=self.try_update, args=(True,), daemon=True).start()

    def on_quit(self, *_):
        self.stop_event.set()
        self.refresh_event.set()

    def run(self):
        log.info("Inicio %s %s", APP_NAME, VERSION)
        threading.Thread(target=self.update_loop, daemon=True).start()
        while not self.stop_event.is_set():
            self.poll_once()
            self.refresh_event.wait(POLL_S)
            self.refresh_event.clear()
        for tray in [*self.icons.values(), self.placeholder]:
            if tray:
                tray.stop()


def main():
    if not single_instance():
        return 0
    App().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
