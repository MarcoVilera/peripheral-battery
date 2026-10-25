"""Iconos: el de la bandeja (Qt) y el del ejecutable/instalador (PIL -> .ico)."""
from PIL import Image, ImageDraw

GREEN = (22, 163, 74)


def tray_icon(light_taskbar, alert=False):
    """Bateria generica que contrasta con la barra; punto rojo si algun dispositivo esta bajo."""
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

    fg = QColor("#1b1b1b") if light_taskbar else QColor("#ffffff")
    icon = QIcon()
    for size in (16, 20, 24, 32, 48, 64):
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        s = size / 32  # todo se dibuja en una grilla de 32x32
        stroke = max(1.0, 2.2 * s)
        p.setPen(QPen(fg, stroke))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(2 * s, 9 * s, 24 * s, 14 * s), 3 * s, 3 * s)
        p.setPen(Qt.NoPen)
        p.setBrush(fg)
        p.drawRoundedRect(QRectF(27 * s, 13 * s, 3 * s, 6 * s), 1 * s, 1 * s)
        for i in range(3):  # tres barras de carga
            p.drawRoundedRect(QRectF((5.5 + i * 6.5) * s, 12.5 * s, 4.5 * s, 7 * s), 1 * s, 1 * s)
        if alert:
            r = 6.5 * s
            p.setPen(QPen(QColor("#202020") if not light_taskbar else QColor("#f3f3f3"), 1.5 * s))
            p.setBrush(QColor("#e81123"))
            p.drawEllipse(QRectF(32 * s - 2 * r - 0.5, 0.5, 2 * r, 2 * r))
        p.end()
        icon.addPixmap(pm)
    return icon


def app_icon():
    """Icono del ejecutable/instalador: una bateria."""
    img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((20, 60, 216, 196), radius=24, outline="white", width=14, fill=(30, 30, 30))
    d.rounded_rectangle((216, 100, 240, 156), radius=8, fill="white")
    d.rounded_rectangle((44, 84, 160, 172), radius=10, fill=GREEN)
    return img


if __name__ == "__main__":
    # python icons.py -> genera assets/icon.ico para PyInstaller e Inno Setup
    from pathlib import Path

    out = Path(__file__).with_name("assets")
    out.mkdir(exist_ok=True)
    app_icon().save(out / "icon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (256, 256)])
    print(out / "icon.ico")
