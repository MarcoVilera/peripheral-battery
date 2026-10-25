from dataclasses import dataclass


class DeviceError(RuntimeError):
    """El dispositivo esta conectado por USB pero no se pudo leer la bateria."""


@dataclass
class Status:
    pct: int
    charging: bool
    connection: str  # p. ej. "dongle 2.4GHz", "cable USB"


class Driver:
    """Un modelo de dispositivo. Para agregar uno nuevo: subclase + registrarla en devices/__init__.py."""

    id = ""  # identificador estable, sin espacios
    name = ""  # nombre que se muestra
    kind = "mouse"  # "mouse", "keyboard", "headset"...

    def read(self):
        """Devuelve Status, None si el dispositivo no esta conectado, o lanza DeviceError."""
        raise NotImplementedError
