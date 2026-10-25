from .base import DeviceError, Driver, Status
from .fantech_wg9rd import FantechKanataWG9RD

# Drivers soportados. Para agregar un dispositivo, crea su modulo y suma su clase aca.
DRIVERS = [FantechKanataWG9RD()]

__all__ = ["DRIVERS", "DeviceError", "Driver", "Status"]
