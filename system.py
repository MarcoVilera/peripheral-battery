"""Integracion con Windows: tema, autoarranque e instancia unica."""
import ctypes
import sys
import winreg

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "PeripheralBattery"  # mismo nombre que usa installer.iss
PERSONALIZE_KEY = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
DEFAULT_ACCENT = (0, 120, 212)


def _read_dword(path, name, default):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as k:
            return winreg.QueryValueEx(k, name)[0]
    except OSError:
        return default


def taskbar_is_light():
    """Tema de la barra de tareas y los flyouts del sistema (no el de las apps)."""
    return bool(_read_dword(PERSONALIZE_KEY, "SystemUsesLightTheme", 0))


def accent_rgb():
    """Color de acento de Windows como (r, g, b)."""
    abgr = _read_dword(r"Software\Microsoft\Windows\DWM", "AccentColor", None)
    if abgr is None:
        return DEFAULT_ACCENT
    return abgr & 0xFF, (abgr >> 8) & 0xFF, (abgr >> 16) & 0xFF


def autostart_supported():
    # Desde el codigo fuente sys.executable es python.exe: solo tiene sentido instalada.
    return bool(getattr(sys, "frozen", False))


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


def round_corners(hwnd):
    """Esquinas redondeadas y sombra nativas de Windows 11 (no hace nada en Windows 10)."""
    try:
        pref = ctypes.c_int(2)  # DWMWCP_ROUND
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd), 33, ctypes.byref(pref), ctypes.sizeof(pref)
        )
    except (OSError, AttributeError):
        pass
