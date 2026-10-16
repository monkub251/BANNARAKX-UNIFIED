"""Animated scrolling numbers. Cheap by design: each column is pre-rendered once and only
blitted with an offset (~15 fps) and the animation pauses whenever the window is not active."""
from __future__ import annotations

import random
import time

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPixmap, QRadialGradient
from PySide6.QtWidgets import QWidget

from . import theme


class MatrixBackground(QWidget):
    CW, LH = 22, 18

    def __init__(self, parent, mono_family: str):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._mono = mono_family
        self._cols: list[list] = []
        self._strip_h = 0
        self._vignette: QPixmap | None = None
        self._last = time.monotonic()
        self._timer = QTimer(self)
        self._timer.setInterval(66)
        self._timer.timeout.connect(self._tick)

    def start(self):
        self._last = time.monotonic()
        if not self._timer.isActive():
            self._timer.start()

    def stop(self):
        self._timer.stop()

    def resizeEvent(self, e):
        self._build()

    def _build(self):
        w, h = max(self.width(), 1), max(self.height(), 1)
        self._strip_h = (h // self.LH + 1) * self.LH
        rnd = random.Random(7)
        f = QFont(self._mono)
        f.setPixelSize(13)
        self._cols = []
        for i in range(w // self.CW + 1):
            pm = QPixmap(self.CW, self._strip_h)
            pm.fill(Qt.transparent)
            p = QPainter(pm)
            p.setFont(f)
            seg = rnd.randint(8, 20)
            k = rnd.randint(0, seg)
            accent = rnd.random() < 0.08
            for row in range(self._strip_h // self.LH):
                k = (k + 1) % seg
                a = int(10 + 78 * (k / seg) ** 2.2)
                base = QColor(34, 211, 238) if accent else QColor(139, 92, 246)
                base.setAlpha(a)
                p.setPen(base)
                p.drawText(QRectF(0, row * self.LH, self.CW, self.LH), Qt.AlignCenter,
                           rnd.choice("0123456789ABCDEF"))
            p.end()
            self._cols.append([pm, rnd.uniform(10, 38), rnd.uniform(0, self._strip_h)])
        v = QPixmap(w, h)
        v.fill(Qt.transparent)
        p = QPainter(v)
        g = QRadialGradient(w / 2, h / 2, max(w, h) * 0.62)
        g.setColorAt(0.0, QColor(6, 4, 14, 215))
        g.setColorAt(0.55, QColor(6, 4, 14, 110))
        g.setColorAt(1.0, QColor(6, 4, 14, 0))
        p.fillRect(0, 0, w, h, g)
        p.end()
        self._vignette = v

    def _tick(self):
        now = time.monotonic()
        dt = min(now - self._last, 0.2)
        self._last = now
        for c in self._cols:
            c[2] = (c[2] + c[1] * dt) % self._strip_h
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        g = QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0, QColor(theme.BG))
        g.setColorAt(1, QColor("#0a0618"))
        p.fillRect(self.rect(), g)
        for i, (pm, _spd, off) in enumerate(self._cols):
            x = i * self.CW
            y = int(off)
            p.drawPixmap(x, y, pm)
            p.drawPixmap(x, y - self._strip_h, pm)
        if self._vignette:
            p.drawPixmap(0, 0, self._vignette)
