"""Peripheral Battery: icono en la bandeja con un panel que muestra la bateria de cada dispositivo."""
import logging
import logging.handlers
import sys
import threading
import time

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

import icons
import system
import updater
from devices import DRIVERS, DeviceError
from estimator import Estimator, format_estimate
from flyout import Flyout
from settings import DATA_DIR, Settings
from version import GITHUB_REPO, VERSION

APP_NAME = "Peripheral Battery"
POLL_S = 60
POLL_OPEN_S = 1  # mientras el panel esta abierto: casi tiempo real
UPDATE_CHECK_S = 6 * 60 * 60
CLICK_REOPEN_GUARD_S = 0.3

# Log con rotacion: como maximo ~512 KB en disco (app.log + app.log.1).
_handler = logging.handlers.RotatingFileHandler(
    DATA_DIR / "app.log", maxBytes=256 * 1024, backupCount=1, encoding="utf-8"
)
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[_handler])
log = logging.getLogger("app")


def read_all():
    """Lee todos los drivers. Devuelve la lista de dispositivos presentes como dicts."""
    out = []
    for drv in DRIVERS:
        base = {"id": drv.id, "name": drv.name, "kind": drv.kind}
        try:
            st = drv.read()
        except DeviceError as e:
            out.append({**base, "error": str(e)})
            continue
        except Exception as e:
            log.exception("Error leyendo %s", drv.id)
            out.append({**base, "error": f"Error: {e}"})
            continue
        if st is not None:
            out.append({**base, "pct": st.pct, "charging": st.charging, "connection": st.connection})
    return out


class Worker(QObject):
    """Hilos de lectura y de actualizaciones; se comunican con la UI por señales."""

    devices = Signal(list)
    notify = Signal(str)
    update_status = Signal(str)
    quit_for_update = Signal()

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.stop = threading.Event()
        self.refresh = threading.Event()
        self.fast = False  # True mientras el panel esta abierto
        self.estimator = Estimator()

    def start(self):
        threading.Thread(target=self._poll_loop, daemon=True).start()
        if GITHUB_REPO:
            threading.Thread(target=self._update_loop, daemon=True).start()

    def _poll_loop(self):
        last = None
        while not self.stop.is_set():
            devs = read_all()
            for d in devs:
                if "pct" in d:
                    hours = self.estimator.update(d["id"], d["pct"], d["charging"])
                    d["estimate"] = format_estimate(hours, d["charging"])
            summary = "; ".join(
                f"{d['name']}: " + (d["error"] if "error" in d else f"{d['pct']}%" + (" (cargando)" if d["charging"] else ""))
                for d in devs
            ) or "Ningún dispositivo"
            if summary != last:
                log.info(summary)
                last = summary
            self.devices.emit(devs)
            self.refresh.wait(POLL_OPEN_S if self.fast else POLL_S)
            self.refresh.clear()

    def _update_loop(self):
        # Primera revision al minuto de arrancar para no competir con el inicio de Windows.
        delay = 60
        while not self.stop.wait(delay):
            if self.settings["auto_update"]:  # el usuario puede desactivarlo en Opciones
                self.check_updates(manual=False)
            delay = UPDATE_CHECK_S

    def check_updates(self, manual):
        if manual:
            self.update_status.emit("Buscando...")
        try:
            found = updater.check()
        except Exception:
            log.exception("Error buscando actualizaciones")
            self.update_status.emit("No se pudo buscar actualizaciones")
            return
        if not found:
            self.update_status.emit(f"Versión {VERSION} · al día")
            return
        new_version, url = found
        log.info("Actualizando a %s desde %s", new_version, url)
        self.update_status.emit(f"Instalando {new_version}...")
        self.notify.emit(f"Instalando la versión {new_version}...")
        try:
            updater.download_and_install(url)
        except Exception:
            log.exception("Error instalando la actualizacion")
            self.update_status.emit("No se pudo instalar la actualización")
            return
        self.quit_for_update.emit()


class TrayApp(QObject):
    def __init__(self, qapp):
        super().__init__()
        self.qapp = qapp
        self.settings = Settings()
        self.devices = []
        self.low_warned = set()
        self.icon_state = None  # (tema claro, alerta) del icono actual de la bandeja

        self.worker = Worker(self.settings)
        self.flyout = Flyout(self.settings, VERSION)
        self.tray = QSystemTrayIcon()
        self.refresh_tray_icon(False)
        self.tray.setToolTip(APP_NAME)
        self.tray.activated.connect(self.on_activated)

        menu = QMenu()
        open_action = QAction("Abrir", menu)
        open_action.triggered.connect(self.open_flyout)
        quit_action = QAction("Salir", menu)
        quit_action.triggered.connect(self.quit)
        menu.addAction(open_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.menu = menu  # referencia para que Qt no lo destruya

        self.worker.devices.connect(self.on_devices)
        self.worker.notify.connect(self.notify)
        self.worker.update_status.connect(self.flyout.set_update_status)
        self.worker.quit_for_update.connect(self.quit)
        self.flyout.autostart_toggled.connect(self.on_autostart)
        self.flyout.alert_toggled.connect(lambda v: self.settings.set("low_battery_alert", v))
        self.flyout.auto_update_toggled.connect(lambda v: self.settings.set("auto_update", v))
        self.flyout.threshold_changed.connect(self.on_threshold)
        self.flyout.check_updates.connect(
            lambda: threading.Thread(target=self.worker.check_updates, args=(True,), daemon=True).start()
        )
        self.flyout.quit_requested.connect(self.quit)
        self.flyout.visibility_changed.connect(self.on_flyout_visible)

    def run(self):
        log.info("Inicio %s %s", APP_NAME, VERSION)
        updater.cleanup_installers()
        self.tray.show()
        self.worker.start()
        return self.qapp.exec()

    # --- datos ---

    def on_devices(self, devices):
        self.devices = devices
        self.flyout.set_devices(devices)
        threshold = self.settings["low_battery_threshold"]
        any_low = False
        for d in devices:
            if "pct" not in d:
                continue
            low = d["pct"] <= threshold and not d["charging"]
            any_low |= low
            if d["charging"] or d["pct"] > threshold + 5:  # margen para no repetir el aviso
                self.low_warned.discard(d["id"])
            elif low and d["id"] not in self.low_warned and self.settings["low_battery_alert"]:
                self.low_warned.add(d["id"])
                self.notify(f"A {d['name']} le queda {d['pct']}% de batería.")
        self.refresh_tray_icon(any_low)

    def refresh_tray_icon(self, alert):
        # Solo se regenera si cambio algo: con el panel abierto esto corre cada segundo.
        state = (system.taskbar_is_light(), alert)
        if state != self.icon_state:
            self.icon_state = state
            self.tray.setIcon(icons.tray_icon(*state))

    def notify(self, msg):
        self.tray.showMessage(APP_NAME, msg, QSystemTrayIcon.Information, 5000)

    # --- panel ---

    def on_activated(self, reason):
        if reason != QSystemTrayIcon.Trigger:
            return
        if self.flyout.isVisible():
            self.flyout.close_flyout()
        elif time.monotonic() - self.flyout.last_hidden < CLICK_REOPEN_GUARD_S:
            # El clic en el icono ya cerro el panel al quitarle el foco: no reabrir.
            pass
        else:
            self.open_flyout()

    def open_flyout(self):
        self.flyout.open()

    def on_flyout_visible(self, visible):
        self.worker.fast = visible
        if visible:
            self.worker.refresh.set()  # lectura fresca al abrir

    # --- opciones ---

    def on_autostart(self, enabled):
        try:
            system.set_autostart(enabled)
            log.info("Iniciar con Windows: %s", enabled)
        except OSError:
            log.exception("No se pudo cambiar el inicio con Windows")

    def on_threshold(self, value):
        self.settings.set("low_battery_threshold", value)
        self.low_warned.clear()
        self.on_devices(self.devices)

    def quit(self):
        self.worker.stop.set()
        self.worker.refresh.set()
        self.tray.hide()
        self.qapp.quit()


def main():
    if not system.single_instance():
        return 0
    qapp = QApplication(sys.argv)
    qapp.setQuitOnLastWindowClosed(False)
    return TrayApp(qapp).run()


if __name__ == "__main__":
    sys.exit(main())
