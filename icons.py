"""Dibuja el icono de la bandeja: el porcentaje sobre un fondo segun el nivel."""
from PIL import Image, ImageDraw, ImageFont

SIZE = 64
GREEN, YELLOW, RED = (22, 163, 74), (202, 138, 4), (220, 38, 38)
BLUE, GRAY = (37, 99, 235), (100, 100, 100)


def _font(size):
    for name in ("arialbd.ttf", "segoeuib.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _level_color(pct):
    if pct > 50:
        return GREEN
    if pct > 20:
        return YELLOW
    return RED


def render(pct=None, charging=False):
    """pct None = sin lectura (icono gris con '--')."""
    if pct is None:
        bg, text = GRAY, "--"
    else:
        bg, text = (BLUE if charging else _level_color(pct)), str(pct)
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, SIZE - 1, SIZE - 1), radius=12, fill=bg)
    # Los iconos de la bandeja se ven a 16-32 px: el texto tiene que ocupar casi todo.
    font = _font(46 if len(text) <= 2 else 32)
    d.text((SIZE / 2, SIZE / 2 + 1), text, font=font, fill="white", anchor="mm")
    return img


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
