"""Estima el tiempo de bateria restante y el tiempo para completar la carga.

Los dispositivos solo informan el porcentaje, asi que se mide la velocidad (% por hora)
mientras la app esta abierta: de descarga cuando se usa y de carga cuando esta enchufado.
Los tramos se cortan si pasa mucho tiempo sin lecturas (PC apagada, app cerrada) y lo
aprendido se guarda en disco para tener una estimacion desde el principio la proxima vez.
"""
import json
import time

from settings import DATA_DIR

_FILE = DATA_DIR / "battery_stats.json"
GAP_S = 15 * 60  # mas que esto sin lecturas = se corta el tramo
SETTLE_S = 10 * 60  # tras desconectar el cargador el % baja rapido al principio: no medir


class Track:
    """Mide una direccion (descarga o carga) en tramos y acumula el historial."""

    def __init__(self, direction, min_change, min_time_s, max_history_s, data=None):
        self.direction = direction  # -1 descarga, +1 carga
        self.min_change, self.min_time_s, self.max_history_s = min_change, min_time_s, max_history_s
        d = data or {}
        self.change = d.get("change", 0.0)
        self.time = d.get("time", 0.0)
        self.seg = d.get("seg")  # [inicio_t, inicio_pct, ultimo_pct, t_del_ultimo_cambio]

    def to_dict(self):
        return {"change": self.change, "time": self.time, "seg": self.seg}

    def sample(self, pct, now, gap):
        """Registra una lectura en esta direccion. Devuelve True si cambio el estado."""
        seg = self.seg
        if seg and (gap or (pct - seg[2]) * self.direction < 0):  # gap o el % fue para el otro lado
            self.commit()
            seg = None
        if seg is None:
            self.seg = [now, pct, pct, now]
            return True
        if pct != seg[2]:
            seg[2], seg[3] = pct, now
            return True
        return False

    def commit(self):
        """Suma el tramo actual al historial. Solo cuenta hasta el ultimo cambio de %,
        asi el tiempo despues del ultimo salto no infla la duracion."""
        if self.seg:
            t0, p0, p1, t1 = self.seg
            moved = (p1 - p0) * self.direction
            if moved >= 1 and t1 > t0:
                self.change += moved
                self.time += t1 - t0
                if self.time > self.max_history_s:
                    k = self.max_history_s / self.time
                    self.change *= k
                    self.time *= k
        self.seg = None

    def rate_per_hour(self):
        change, elapsed = self.change, self.time
        if self.seg:
            t0, p0, p1, t1 = self.seg
            change += (p1 - p0) * self.direction
            elapsed += t1 - t0
        if change < self.min_change or elapsed < self.min_time_s:
            return None
        return change / (elapsed / 3600)


def _new_device(data=None):
    d = data or {}
    return {
        "discharge": Track(-1, 3, 60 * 60, 48 * 3600, d.get("discharge")),
        "charge": Track(+1, 3, 5 * 60, 10 * 3600, d.get("charge")),
        "last_t": d.get("last_t", 0),
        "charge_end": d.get("charge_end", 0),
    }


class Estimator:
    def __init__(self):
        try:
            raw = json.loads(_FILE.read_text())
        except (OSError, ValueError):
            raw = {}
        self.devices = {k: _new_device(v) for k, v in raw.items() if isinstance(v, dict)}

    def _save(self):
        out = {
            k: {
                "discharge": d["discharge"].to_dict(),
                "charge": d["charge"].to_dict(),
                "last_t": d["last_t"],
                "charge_end": d["charge_end"],
            }
            for k, d in self.devices.items()
        }
        try:
            _FILE.write_text(json.dumps(out))
        except OSError:
            pass

    def update(self, dev_id, pct, charging, now=None):
        """Registra una lectura. Devuelve horas estimadas (restantes o para completar la carga) o None."""
        now = now or time.time()
        d = self.devices.setdefault(dev_id, _new_device())
        gap = now - d["last_t"] > GAP_S
        dis, chg = d["discharge"], d["charge"]
        changed = False
        if charging:
            if dis.seg:
                dis.commit()
                changed = True
            changed |= chg.sample(pct, now, gap)
            d["charge_end"] = now
        else:
            if chg.seg:
                chg.commit()
                changed = True
            if dis.seg or now - d["charge_end"] >= SETTLE_S:
                changed |= dis.sample(pct, now, gap)
        d["last_t"] = now
        if changed:
            self._save()
        return self.estimate(dev_id, pct, charging)

    def estimate(self, dev_id, pct, charging):
        d = self.devices.get(dev_id)
        if not d:
            return None
        if charging:
            rate = d["charge"].rate_per_hour()
            return (100 - pct) / rate if rate and pct < 100 else None
        rate = d["discharge"].rate_per_hour()
        return pct / rate if rate else None


def _fmt_duration(hours):
    if hours < 1:
        return f"~{max(1, round(hours * 60))} min"
    if hours < 48:
        h = int(hours)
        m = round((hours - h) * 60 / 5) * 5
        if hours < 5 and m:  # en tiempos cortos los minutos importan
            return f"~{h} h {m:02d} min" if m < 60 else f"~{h + 1} h"
        return f"~{round(hours)} h"
    return f"~{round(hours / 24)} días"


def format_estimate(hours, charging):
    if hours is None:
        return None
    return f"{_fmt_duration(hours)} para completar" if charging else f"{_fmt_duration(hours)} restantes"
