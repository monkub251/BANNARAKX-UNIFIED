from __future__ import annotations

from PySide6.QtCore import (Property, QEasingCurve, QPropertyAnimation, QRectF, Qt, QTimer, Signal)
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (QCheckBox, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget)

from . import theme


class ModeCard(QPushButton):
    """One of the two primary buttons."""

    def __init__(self, tag: str, name: str, blurb: str, accent: str, fonts: theme.Fonts):
        super().__init__()
        self.tag, self.name_, self.blurb, self.accent, self.f = tag, name, blurb, QColor(accent), fonts
        self._glow = 0.0
        self._state_text, self._state_color = "READY", QColor(theme.OK)
        self._pulse = 0.0
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumSize(380, 210)
        self.setFlat(True)
        self.anim = QPropertyAnimation(self, b"glow", self)
        self.anim.setDuration(220)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.pulse_timer = QTimer(self)
        self.pulse_timer.setInterval(90)
        self.pulse_timer.timeout.connect(self._pulse_tick)

    def _get(self): return self._glow
    def _set(self, v):
        self._glow = v
        self.update()
    glow = Property(float, _get, _set)

    def set_state(self, text: str, color: str, pulse: bool = False):
        self._state_text, self._state_color = text, QColor(color)
        if pulse and not self.pulse_timer.isActive():
            self.pulse_timer.start()
        if not pulse:
            self.pulse_timer.stop()
            self._pulse = 0.0
        self.update()

    def _pulse_tick(self):
        self._pulse = (self._pulse + 0.12) % 6.2832
        self.update()

    def enterEvent(self, e):
        if self.isEnabled():
            self.anim.stop(); self.anim.setEndValue(1.0); self.anim.start()

    def leaveEvent(self, e):
        self.anim.stop(); self.anim.setEndValue(0.0); self.anim.start()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        en = self.isEnabled()
        r = QRectF(self.rect()).adjusted(6, 6, -6, -6)
        path = QPainterPath(); path.addRoundedRect(r, 18, 18)
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0, QColor(20, 13, 44, 238)); g.setColorAt(1, QColor(9, 6, 22, 238))
        p.fillPath(path, g)
        a = self.accent
        for i in range(6, 0, -1):  # soft outer glow
            c = QColor(a); c.setAlpha(int(self._glow * 34 / i))
            p.setPen(QPen(c, i * 2.2)); p.drawPath(path)
        c = QColor(a); c.setAlpha(int((110 + 145 * self._glow) if en else 60))
        p.setPen(QPen(c, 1.4 + self._glow)); p.drawPath(path)
        bar = QPainterPath(); bar.addRoundedRect(QRectF(r.left() + 22, r.top() + 24, 4, 34), 2, 2)
        p.fillPath(bar, a)
        x = r.left() + 40; w = r.width() - 64
        fm = QFont(self.f.mono); fm.setPixelSize(11); fm.setLetterSpacing(QFont.AbsoluteSpacing, 3)
        p.setFont(fm); p.setPen(QColor(theme.MUTED))
        p.drawText(QRectF(x, r.top() + 22, w, 16), Qt.AlignLeft | Qt.AlignVCenter, self.tag)
        fd = QFont(self.f.display); fd.setPixelSize(34); fd.setWeight(QFont.Bold); fd.setLetterSpacing(QFont.AbsoluteSpacing, 4)
        p.setFont(fd); p.setPen(QColor(theme.TEXT if en else "#6d6690"))
        p.drawText(QRectF(x, r.top() + 38, w, 44), Qt.AlignLeft | Qt.AlignVCenter, self.name_)
        fb = QFont(self.f.body); fb.setPixelSize(13)
        p.setFont(fb); p.setPen(QColor(theme.LILAC if en else "#5f5885"))
        p.drawText(QRectF(x, r.top() + 90, w, 54), Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, self.blurb)
        # status chip
        pc = QColor(self._state_color)
        if self.pulse_timer.isActive():
            import math
            pc.setAlpha(int(150 + 105 * math.sin(self._pulse)))
        p.setPen(Qt.NoPen); p.setBrush(pc)
        p.drawEllipse(QRectF(x, r.bottom() - 36, 9, 9))
        fs = QFont(self.f.mono); fs.setPixelSize(11); fs.setLetterSpacing(QFont.AbsoluteSpacing, 2)
        p.setFont(fs); p.setPen(self._state_color)
        p.drawText(QRectF(x + 18, r.bottom() - 42, 160, 22), Qt.AlignLeft | Qt.AlignVCenter, self._state_text)
        ac = QColor(a); ac.setAlpha(int((150 + 105 * self._glow) if en else 70)); p.setPen(ac)
        p.drawText(QRectF(r.right() - 190, r.bottom() - 42, 170, 22), Qt.AlignRight | Qt.AlignVCenter,
                   "APPLY  ›" if en else "…")


class Dialog(QDialog):
    """Dark confirm / info dialog. `choice` is the index of the clicked button (or -1)."""

    def __init__(self, parent, fonts: theme.Fonts, title: str, body_html: str,
                 buttons: list[tuple[str, str]], checkbox: str | None = None, checked: bool = True,
                 disabled: set[int] | None = None, accent: str = theme.VIOLET):
        super().__init__(parent)
        self.choice = -1
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(520)
        lay = QVBoxLayout(self); lay.setContentsMargins(26, 24, 26, 22); lay.setSpacing(14)
        t = QLabel(title)
        tf = QFont(fonts.display); tf.setPixelSize(20); tf.setWeight(QFont.Bold); tf.setLetterSpacing(QFont.AbsoluteSpacing, 2)
        t.setFont(tf); t.setStyleSheet(f"color:{accent};")
        lay.addWidget(t)
        body = QLabel(body_html); body.setWordWrap(True); body.setTextFormat(Qt.RichText)
        body.setStyleSheet(f"color:{theme.TEXT}; line-height:150%;")
        lay.addWidget(body)
        self.cb = None
        if checkbox:
            self.cb = QCheckBox(checkbox); self.cb.setChecked(checked); lay.addWidget(self.cb)
        row = QHBoxLayout(); row.setSpacing(10); row.addStretch(1)
        for i, (label, variant) in enumerate(buttons):
            b = QPushButton(label); b.setProperty("variant", variant); b.setCursor(Qt.PointingHandCursor)
            if disabled and i in disabled:
                b.setEnabled(False)
            b.clicked.connect(lambda _=False, i=i: self._pick(i))
            row.addWidget(b)
        lay.addLayout(row)

    def _pick(self, i):
        self.choice = i
        self.accept()
