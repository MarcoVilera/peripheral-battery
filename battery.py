"""Muestra por consola la bateria de los dispositivos soportados conectados."""
import sys

from devices import DRIVERS, DeviceError


def main():
    any_found = False
    for drv in DRIVERS:
        try:
            st = drv.read()
        except DeviceError as e:
            print(f"{drv.name}: {e}")
            any_found = True
            continue
        if st is None:
            continue
        any_found = True
        print(f"{drv.name}: {st.pct}% [{st.connection}]" + (" (cargando)" if st.charging else ""))
    if not any_found:
        print("No hay dispositivos soportados conectados")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
