"""Fantech KANATA WIRELESS WG9RD (dongle 2.4GHz o cable USB).

Protocolo extraido del software oficial de Fantech (msDeviceUtils.js):
  - Feature report ID 6 en la interfaz vendor-defined (usage page 0xFF01).
  - Request:  [6, 0, 0, cmd|0x80, seq, distinguishId, addrLo, addrHi, len, ...]
              cmd 1 = CONNSTA_BATLEV (estado conexion + bateria), len 3
  - Response: [6, ..., [8]=status!=0, [9]=connSta, [10]=batLev, [11]=chip]
              batLev: bit7 = cargando, bits0-6 = porcentaje
"""
import time

import hid

from .base import DeviceError, Driver, Status

VID = 0xB6A4
PIDS = {0x40A1: "dongle 2.4GHz", 0x40A0: "cable USB"}
USAGE_PAGE = 0xFF01
REPORT_ID = 6
CMD_CONNSTA_BATLEV = 0x01
READ_FLAG = 0x80
BEGIN = 9  # BEGINADDRESS en el JS
RETRIES = 5
FEATURE_LEN = 40  # bytes de datos (sin report ID); Windows exige el tamano exacto (41 con ID)


class FantechKanataWG9RD(Driver):
    id = "fantech-kanata-wg9rd"
    name = "Fantech Kanata WG9RD"
    kind = "mouse"

    def __init__(self):
        self._seq = 0

    def _query(self, dev):
        """Devuelve (enlazado, porcentaje, cargando) o None si no hubo respuesta."""
        for _ in range(RETRIES):
            self._seq = (self._seq + 1) & 0xFF
            payload = [0] * FEATURE_LEN
            payload[2] = CMD_CONNSTA_BATLEV | READ_FLAG
            payload[3] = self._seq
            payload[7] = 3  # bytes pedidos: connSta, batLev, chip
            dev.send_feature_report([REPORT_ID] + payload)
            time.sleep(0.08)
            r = dev.get_feature_report(REPORT_ID, FEATURE_LEN + 1)
            if r and len(r) > BEGIN + 1 and r[BEGIN - 1] != 0:
                bat = r[BEGIN + 1]
                return r[BEGIN] != 0, min(bat & 0x7F, 100), bool(bat >> 7)
        return None

    def read(self):
        errors, found = [], False
        for pid, mode in PIDS.items():
            for info in hid.enumerate(VID, pid):
                if info["usage_page"] != USAGE_PAGE:
                    continue
                found = True
                dev = hid.device()
                try:
                    dev.open_path(info["path"])
                    res = self._query(dev)
                except OSError as e:
                    errors.append(f"{mode}: {e}")
                    continue
                finally:
                    dev.close()
                if res is None:
                    continue
                linked, pct, charging = res
                if not linked:
                    raise DeviceError("Dongle conectado, pero el mouse no esta enlazado")
                return Status(pct, charging, mode)
        if not found:
            return None
        if errors:
            raise DeviceError("Error al leer el mouse: " + "; ".join(errors))
        raise DeviceError("Dongle conectado, pero el mouse no responde")
