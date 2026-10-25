"""Panel flotante estilo Windows 11 con la bateria de cada dispositivo y las opciones."""
import time

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QGuiApplication, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import system

WIDTH = 340
MARGIN = 12  # separacion con el borde de la barra de tareas
ICON_FONTS = ["Segoe Fluent Icons", "Segoe MDL2 Assets"]
TEXT_FONTS = ["Segoe UI Variable Text", "Segoe UI"]

GLYPHS = {
    "mouse": "",
    "keyboard": "",
    "headset": "",
    "gamepad": "",
    "other": "",
    "settings": "",
    "back": "",
    "charging": "",
    "warning": "",
}
THRESHOLDS = [10, 15, 20, 25, 30]


def _font(families, px, weight=QFont.Normal):
    f = QFont()
    f.setFamilies(families)
    f.setPixelSize(px)
    f.setWeight(weight)
    return f


def _paint_glyph(widget, glyph, px, color):
    """Dibuja un glifo de Segoe Fluent Icons como figura vectorial suavizada.

    Como texto, Qt lo rasteriza con ClearType y hinting y a 100% de escala queda
    serruchado y con bordes de colores; como QPainterPath queda suave como en Windows 11.
    """
    path = QPainterPath()
    path.addText(0, 0, _font(ICON_FONTS, px), glyph)
    box = path.boundingRect()
    r = widget.rect()
    path.translate(r.center().x() + 0.5 - box.center().x(), r.center().y() + 0.5 - box.center().y())
    p = QPainter(widget)
    p.setRenderHint(QPainter.Antialiasing)
    p.fillPath(path, color)
    p.end()


def _mix(c1, c2, t):
    return QColor(*(round(a + (b - a) * t) for a, b in zip(c1.getRgb()[:3], c2.getRgb()[:3])))


class Palette:
    """Colores segun el tema de la barra de tareas y el acento de Windows."""

    def __init__(self):
        self.light = system.taskbar_is_light()
        accent = QColor(*system.accent_rgb())
        if self.light:
            self.bg, self.card, self.border = QColor("#f3f3f3"), QColor("#fbfbfb"), QColor("#e2e2e2")
            self.text, self.subtext, self.track = QColor("#1b1b1b"), QColor("#5d5d5d"), QColor("#d4d4d4")
            self.hover = QColor("#e9e9e9")
            self.accent = accent
            self.low, self.charging = QColor("#c42b1c"), QColor("#0f7b0f")
        else:
            self.bg, self.card, self.border = QColor("#202020"), QColor("#2b2b2b"), QColor("#3a3a3a")
            self.text, self.subtext, self.track = QColor("#ffffff"), QColor("#c5c5c5"), QColor("#454545")
            self.hover = QColor("#353535")
            # En tema oscuro Windows usa una variante mas clara del acento.
            self.accent = _mix(accent, QColor("white"), 0.35)
            self.low, self.charging = QColor("#ff6b6b"), QColor("#6ccb5f")
        self.on_accent = QColor("black") if self.accent.lightness() > 150 else QColor("white")

    def stylesheet(self):
        p = {k: v.name() for k, v in vars(self).items() if isinstance(v, QColor)}
        return f"""
            #Flyout {{ background: {p['bg']}; border: 1px solid {p['border']}; border-radius: 8px; }}
            QLabel {{ color: {p['text']}; background: transparent; }}
            QLabel[role="sub"] {{ color: {p['subtext']}; }}
            QFrame[role="card"] {{ background: {p['card']}; border: 1px solid {p['border']}; border-radius: 6px; }}
            QPushButton {{
                color: {p['text']}; background: {p['card']}; border: 1px solid {p['border']};
                border-radius: 4px; padding: 5px 14px;
            }}
            QPushButton:hover {{ background: {p['hover']}; }}
            QPushButton[role="icon"] {{ background: transparent; border: none; padding: 4px; border-radius: 4px; }}
            QPushButton[role="icon"]:hover {{ background: {p['hover']}; }}
            QComboBox {{
                color: {p['text']}; background: {p['card']}; border: 1px solid {p['border']};
                border-radius: 4px; padding: 3px 10px;
            }}
            QComboBox:hover {{ background: {p['hover']}; }}
            QComboBox::drop-down {{ border: none; width: 18px; }}
            QComboBox QAbstractItemView {{
                color: {p['text']}; background: {p['card']}; border: 1px solid {p['border']};
                selection-background-color: {p['hover']}; selection-color: {p['text']}; outline: none;
            }}
        """


class Toggle(QAbstractButton):
    """Interruptor estilo Windows 11."""

    def __init__(self, palette, parent=None):
        super().__init__(parent)
        self.pal = palette
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)

    def sizeHint(self):
        return QSize(40, 20)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(0.5, 0.5, 39, 19)
        enabled = self.isEnabled()
        if self.isChecked():
            fill = self.pal.accent if enabled else self.pal.track
            p.setPen(Qt.NoPen)
            p.setBrush(fill)
            p.drawRoundedRect(r, 10, 10)
            p.setBrush(self.pal.on_accent)
            p.drawEllipse(QRectF(24, 4, 12, 12))
        else:
            p.setPen(QPen(self.pal.subtext if enabled else self.pal.track, 1))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r, 10, 10)
            p.setPen(Qt.NoPen)
            p.setBrush(self.pal.subtext if enabled else self.pal.track)
            p.drawEllipse(QRectF(5, 5, 10, 10))


class BatteryBar(QWidget):
    def __init__(self, palette, pct, color, parent=None):
        super().__init__(parent)
        self.pal, self.pct, self.color = palette, pct, color
        self.setFixedHeight(4)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        r = QRectF(self.rect())
        p.setBrush(self.pal.track)
        p.drawRoundedRect(r, 2, 2)
        if self.pct:
            p.setBrush(self.color)
            p.drawRoundedRect(QRectF(0, 0, r.width() * self.pct / 100, r.height()), 2, 2)


class Glyph(QWidget):
    def __init__(self, glyph, px, color, size=None):
        super().__init__()
        self.glyph, self.px, self.color = glyph, px, color
        side = size or px + 4
        self.setFixedSize(side, side)

    def paintEvent(self, _):
        _paint_glyph(self, self.glyph, self.px, self.color)


class IconButton(QPushButton):
    def __init__(self, glyph, color):
        super().__init__()
        self.glyph, self.color = glyph, color

    def paintEvent(self, e):
        super().paintEvent(e)  # fondo de hover segun el stylesheet
        _paint_glyph(self, self.glyph, 16, self.color)


def _label(text, px=13, weight=QFont.Normal, sub=False, families=TEXT_FONTS):
    lb = QLabel(text)
    lb.setFont(_font(families, px, weight))
    if sub:
        lb.setProperty("role", "sub")
    return lb


def _card():
    f = QFrame()
    f.setProperty("role", "card")
    return f


def _icon_button(glyph, tooltip, color):
    b = IconButton(glyph, color)
    b.setProperty("role", "icon")
    b.setToolTip(tooltip)
    b.setCursor(Qt.PointingHandCursor)
    b.setFixedSize(32, 32)
    return b


class Flyout(QWidget):
    autostart_toggled = Signal(bool)
    alert_toggled = Signal(bool)
    auto_update_toggled = Signal(bool)
    threshold_changed = Signal(int)
    check_updates = Signal()
    quit_requested = Signal()
    visibility_changed = Signal(bool)

    def __init__(self, settings, version):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.settings = settings
        self.version = version
        self.last_hidden = 0.0
        self.devices = []
        self.update_status = ""
        self.setObjectName("Flyout")
        self.setAttribute(Qt.WA_StyledBackground)
        self.setFixedWidth(WIDTH)
        self.stack = QStackedWidget()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 16)
        lay.addWidget(self.stack)
        self.rebuild()

    # --- construccion ---

    def rebuild(self):
        """Rehace todo el contenido (se llama al abrir, asi toma cambios de tema)."""
        self.pal = Palette()
        self.setStyleSheet(self.pal.stylesheet())
        current = self.stack.currentIndex() if self.stack.count() else 0
        while self.stack.count():
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            w.deleteLater()
        self.stack.addWidget(self._devices_page())
        self.stack.addWidget(self._settings_page())
        self.stack.setCurrentIndex(current)
        self._fit()

    def _header(self, title, glyph, tooltip, action):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(_label(title, 14, QFont.DemiBold))
        row.addStretch()
        btn = _icon_button(glyph, tooltip, self.pal.text)
        btn.clicked.connect(action)
        row.addWidget(btn)
        return row

    def _devices_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addLayout(self._header("Dispositivos", GLYPHS["settings"], "Opciones", lambda: self._go(1)))
        if not self.devices:
            card = _card()
            cl = QVBoxLayout(card)
            cl.setContentsMargins(14, 18, 14, 18)
            msg = _label("Ningún dispositivo conectado", sub=True)
            msg.setAlignment(Qt.AlignCenter)
            cl.addWidget(msg)
            lay.addWidget(card)
        for dev in self.devices:
            lay.addWidget(self._device_card(dev))
        return page

    def _device_card(self, dev):
        threshold = self.settings["low_battery_threshold"]
        card = _card()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(14, 12, 14, 12)
        cl.setSpacing(10)
        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(Glyph(GLYPHS.get(dev["kind"], GLYPHS["other"]), 22, self.pal.text, 26))
        names = QVBoxLayout()
        names.setSpacing(0)
        names.addWidget(_label(dev["name"], 13, QFont.DemiBold))
        pct = dev.get("pct")
        if dev.get("error"):
            sublabel = _label(dev["error"], 12, sub=True)
            sublabel.setWordWrap(True)
            names.addWidget(sublabel)
        else:
            sub = dev["connection"]
            if dev["charging"]:
                sub += " · Carga completa" if pct >= 100 else " · Cargando"
            names.addWidget(_label(sub, 12, sub=True))
            if dev.get("estimate"):
                # En su propia linea: junto a la conexion no entra y el texto se encimaba.
                names.addWidget(_label(dev["estimate"], 12, sub=True))
        row.addLayout(names, 1)
        if pct is not None:
            if dev["charging"]:
                row.addWidget(Glyph(GLYPHS["charging"], 14, self.pal.charging))
            pl = _label(f"{pct}%", 18, QFont.DemiBold)
            if pct <= threshold and not dev["charging"]:
                pl.setStyleSheet(f"color: {self.pal.low.name()}")
            row.addWidget(pl)
        else:
            row.addWidget(Glyph(GLYPHS["warning"], 16, self.pal.subtext))
        cl.addLayout(row)
        if pct is not None:
            color = (
                self.pal.charging if dev["charging"]
                else self.pal.low if pct <= threshold
                else self.pal.accent
            )
            cl.addWidget(BatteryBar(self.pal, pct, color))
        return card

    def _setting_row(self, title, subtitle, control):
        card = _card()
        row = QHBoxLayout(card)
        row.setContentsMargins(14, 10, 14, 10)
        texts = QVBoxLayout()
        texts.setSpacing(0)
        texts.addWidget(_label(title))
        if subtitle:
            texts.addWidget(_label(subtitle, 12, sub=True))
        row.addLayout(texts, 1)
        row.addWidget(control)
        return card

    def _settings_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        lay.addLayout(self._header("Opciones", GLYPHS["back"], "Volver", lambda: self._go(0)))

        auto = Toggle(self.pal)
        auto.setChecked(system.autostart_enabled())
        auto.setEnabled(system.autostart_supported())
        auto.toggled.connect(self.autostart_toggled)
        sub = None if system.autostart_supported() else "Solo en la app instalada"
        lay.addWidget(self._setting_row("Iniciar con Windows", sub, auto))

        alert = Toggle(self.pal)
        alert.setChecked(self.settings["low_battery_alert"])
        alert.toggled.connect(self.alert_toggled)
        lay.addWidget(self._setting_row("Avisar con batería baja", "Notificación de Windows", alert))

        combo = QComboBox()
        combo.addItems([f"{t}%" for t in THRESHOLDS])
        cur = self.settings["low_battery_threshold"]
        combo.setCurrentIndex(THRESHOLDS.index(cur) if cur in THRESHOLDS else 1)
        combo.currentIndexChanged.connect(lambda i: self.threshold_changed.emit(THRESHOLDS[i]))
        combo.setCursor(Qt.PointingHandCursor)
        lay.addWidget(self._setting_row("Batería baja", "Por debajo de este nivel", combo))

        upd = QPushButton("Buscar")
        upd.setCursor(Qt.PointingHandCursor)
        upd.clicked.connect(self.check_updates)
        self.update_label = _label(self.update_status or f"Versión {self.version}", 12, sub=True)
        card = self._setting_row("Actualizaciones", None, upd)
        card.layout().itemAt(0).layout().addWidget(self.update_label)
        lay.addWidget(card)

        auto_upd = Toggle(self.pal)
        auto_upd.setChecked(self.settings["auto_update"])
        auto_upd.toggled.connect(self.auto_update_toggled)
        lay.addWidget(self._setting_row("Actualizar automáticamente", "Consulta GitHub al iniciar y cada 6 h", auto_upd))

        foot = QHBoxLayout()
        foot.setContentsMargins(0, 6, 0, 0)
        foot.addWidget(_label(f"Peripheral Battery {self.version}", 12, sub=True))
        foot.addStretch()
        quit_btn = QPushButton("Salir")
        quit_btn.setCursor(Qt.PointingHandCursor)
        quit_btn.clicked.connect(self.quit_requested)
        foot.addWidget(quit_btn)
        lay.addLayout(foot)
        return page

    def _go(self, index):
        self.stack.setCurrentIndex(index)
        self._fit()

    def _fit(self):
        page = self.stack.currentWidget()
        if page is None:
            return
        page.adjustSize()
        self.stack.setFixedHeight(page.sizeHint().height())
        self.adjustSize()
        if self.isVisible():
            self.place()

    # --- datos ---

    def set_devices(self, devices):
        if devices == self.devices:
            return  # sin cambios: no redibujar (evita parpadeo con la lectura cada 1 s)
        self.devices = devices
        if self.isVisible():
            page = self.stack.currentIndex()
            old = self.stack.widget(0)
            self.stack.removeWidget(old)
            old.deleteLater()
            self.stack.insertWidget(0, self._devices_page())
            self.stack.setCurrentIndex(page)
            self._fit()

    def set_update_status(self, text):
        self.update_status = text
        if self.isVisible():
            self.update_label.setText(text)

    # --- mostrar / ocultar ---

    def place(self):
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        avail, full = screen.availableGeometry(), screen.geometry()
        x = avail.right() - self.width() - MARGIN + 1
        y = avail.bottom() - self.height() - MARGIN + 1
        if avail.left() > full.left():  # barra a la izquierda
            x = avail.left() + MARGIN
        if avail.top() > full.top():  # barra arriba
            y = avail.top() + MARGIN
        self.move(x, y)

    def open(self):
        self.stack.setCurrentIndex(0)
        self.rebuild()
        self.place()
        self.show()
        system.round_corners(int(self.winId()))
        self.raise_()
        self.activateWindow()

    def close_flyout(self):
        self.last_hidden = time.monotonic()
        self.hide()

    def showEvent(self, e):
        super().showEvent(e)
        self.visibility_changed.emit(True)

    def hideEvent(self, e):
        super().hideEvent(e)
        self.visibility_changed.emit(False)

    def changeEvent(self, e):
        super().changeEvent(e)
        if e.type() == e.Type.ActivationChange and self.isVisible() and not self.isActiveWindow():
            # Clic fuera del panel: se cierra como los flyouts de Windows.
            if QApplication.activePopupWidget() is None:
                self.close_flyout()
