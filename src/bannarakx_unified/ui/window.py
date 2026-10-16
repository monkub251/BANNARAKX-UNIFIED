from __future__ import annotations

import html
import time

from PySide6.QtCore import QObject, QPropertyAnimation, QRectF, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QMainWindow, QPushButton, QTextEdit,
                               QVBoxLayout, QWidget)

from .. import APP_NAME, __version__, integrity
from ..common import Result, is_admin
from ..paths import assets_dir
from ..tweaks_pro import select
from . import theme
from .matrix import MatrixBackground
from .widgets import Dialog, ModeCard

LEVEL_COLOR = {"info": theme.LILAC, "ok": theme.OK, "warn": theme.WARN, "bad": theme.BAD, "dim": theme.MUTED}


class Worker(QThread):
    log = Signal(str, str)
    done = Signal(object)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        try:
            res = self.fn(lambda m, l="info": self.log.emit(m, l))
        except Exception as e:  # never let a worker crash the app
            res = Result(False, "ERROR", "Unexpected error - nothing was reported as done.", [repr(e)])
        self.done.emit(res)


class IntegrityWorker(QThread):
    done = Signal(bool, str)

    def run(self):
        try:
            a, pa = integrity.verify("unlimited/")
            b, pb = True, []
            from ..mode_pro import PRO_EXE
            from ..paths import originals_dir
            if (originals_dir() / PRO_EXE).is_file():  # optional file
                b, pb = integrity.verify("pro/")
        except Exception as e:
            self.done.emit(False, f"check failed: {e}")
            return
        self.done.emit(a and b, "; ".join(pa + pb))


class Stage(QWidget):
    def __init__(self, fonts):
        super().__init__()
        self.bg = MatrixBackground(self, fonts.mono)
        self.fg = QWidget(self)
        self.fg.setAttribute(Qt.WA_TranslucentBackground)

    def resizeEvent(self, e):
        self.bg.setGeometry(self.rect())
        self.fg.setGeometry(self.rect())
        self.bg.lower()


def circular_logo(path: str, size: int) -> QPixmap:
    src = QPixmap(path)
    out = QPixmap(size, size)
    out.fill(Qt.transparent)
    if src.isNull():
        return out
    p = QPainter(out)
    p.setRenderHint(QPainter.Antialiasing); p.setRenderHint(QPainter.SmoothPixmapTransform)
    clip = QPainterPath(); clip.addEllipse(2, 2, size - 4, size - 4)
    p.fillPath(clip, QColor(18, 12, 40))
    p.setClipPath(clip)
    p.drawPixmap(2, 2, src.scaled(size - 4, size - 4, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    p.setClipping(False)
    p.setPen(QPen(QColor(theme.VIOLET), 2)); p.setBrush(Qt.NoBrush)
    p.drawEllipse(QRectF(1, 1, size - 2, size - 2))
    p.end()
    return out


class MainWindow(QMainWindow):
    def __init__(self, unlimited, pro, fonts: theme.Fonts, demo: bool = False):
        super().__init__()
        self.unl, self.pro, self.f, self.demo = unlimited, pro, fonts, demo
        self.worker: Worker | None = None
        self.setWindowTitle(APP_NAME + ("  [DEMO]" if demo else ""))
        ico = assets_dir() / "logo.ico"
        if ico.exists():
            self.setWindowIcon(QIcon(str(ico)))
        self.setMinimumSize(940, 700)
        self.resize(1000, 720)

        self.stage = Stage(fonts)
        self.setCentralWidget(self.stage)
        root = QVBoxLayout(self.stage.fg)
        root.setContentsMargins(36, 28, 36, 22); root.setSpacing(18)

        # ---- header -------------------------------------------------------------------
        head = QHBoxLayout(); head.setSpacing(18)
        logo = QLabel(); logo.setPixmap(circular_logo(str(assets_dir() / "logo.png"), 84)); logo.setFixedSize(84, 84)
        head.addWidget(logo)
        col = QVBoxLayout(); col.setSpacing(2)
        title = QLabel("BANNARAKX")
        tf = QFont(fonts.display); tf.setPixelSize(40); tf.setWeight(QFont.Bold); tf.setLetterSpacing(QFont.AbsoluteSpacing, 8)
        title.setFont(tf)
        sub = QLabel("UNIFIED OPTIMIZER   ·   UNLIMITED × PRO")
        sf = QFont(fonts.mono); sf.setPixelSize(12); sf.setLetterSpacing(QFont.AbsoluteSpacing, 3)
        sub.setFont(sf); sub.setStyleSheet(f"color:{theme.VIOLET};")
        col.addStretch(1); col.addWidget(title); col.addWidget(sub); col.addStretch(1)
        head.addLayout(col); head.addStretch(1)
        self.pill = QLabel("ACTIVE MODE  ·  NONE")
        pf = QFont(fonts.mono); pf.setPixelSize(12); pf.setLetterSpacing(QFont.AbsoluteSpacing, 2)
        self.pill.setFont(pf)
        self.pill.setStyleSheet(f"color:{theme.LILAC}; background:rgba(139,92,246,0.14); border:1px solid {theme.LINE};"
                                "border-radius:14px; padding:7px 16px;")
        head.addWidget(self.pill, 0, Qt.AlignTop)
        root.addLayout(head)

        # ---- the two primary buttons -------------------------------------------------
        cards = QHBoxLayout(); cards.setSpacing(24)
        self.c_unl = ModeCard("BAT GAMEPLAY", "UNLIMITED",
                              "ชุดต้นฉบับ ULTIMATE สำหรับสายไม้ — ปรับเน็ต เกมโหมด อินพุต และบริการ ให้ลื่นและนิ่ง",
                              theme.VIOLET, fonts)
        self.c_pro = ModeCard("KNIFE GAMEPLAY", "PRO",
                              "ชั้น MAX เฉพาะสายมีด — คลิกไว เมาส์ 1:1 เฟรมนิ่ง ตัวจับเวลาละเอียด ปรับแล้วคืนค่าได้ครบ",
                              theme.MAGENTA, fonts)
        cards.addWidget(self.c_unl); cards.addWidget(self.c_pro)
        root.addLayout(cards, 1)
        self.c_unl.clicked.connect(lambda: self.on_mode("unlimited"))
        self.c_pro.clicked.connect(lambda: self.on_mode("pro"))

        # ---- reset + integrity ---------------------------------------------------------
        row = QHBoxLayout(); row.setSpacing(16)
        self.btn_reset = QPushButton("RESET"); self.btn_reset.setProperty("variant", "danger")
        self.btn_reset.setCursor(Qt.PointingHandCursor); self.btn_reset.setMinimumWidth(170)
        self.btn_reset.clicked.connect(self.on_reset)
        row.addWidget(self.btn_reset)
        hint = QLabel("คืนค่าเดิมแยกทีละโหมด — รีเซ็ตโหมดหนึ่งจะไม่แตะอีกโหมด")
        hint.setStyleSheet(f"color:{theme.MUTED};")
        row.addWidget(hint); row.addStretch(1)
        self.integ = QLabel("ORIGINAL FILES  ·  CHECKING…")
        xf = QFont(fonts.mono); xf.setPixelSize(11); xf.setLetterSpacing(QFont.AbsoluteSpacing, 2)
        self.integ.setFont(xf); self.integ.setStyleSheet(f"color:{theme.MUTED};")
        row.addWidget(self.integ)
        root.addLayout(row)

        self.log_view = QTextEdit(); self.log_view.setObjectName("log"); self.log_view.setReadOnly(True)
        self.log_view.setFixedHeight(168)
        root.addWidget(self.log_view)
        foot = QLabel(f"v{__version__}   ·   ไม่มีบริการเบื้องหลัง   ·   ทุกการเปลี่ยนแปลงย้อนกลับได้"
                      + ("   ·   DEMO: ไม่แตะเครื่องจริง" if demo else ""))
        foot.setStyleSheet(f"color:{theme.MUTED}; font-size:11px;")
        root.addWidget(foot)

        self.refresh()
        QApplication.instance().applicationStateChanged.connect(self._app_state)
        self.stage.bg.start()
        self._boot()
        self.iw = IntegrityWorker(); self.iw.done.connect(self._integrity); self.iw.start()

    # ---- helpers -------------------------------------------------------------------------
    def _app_state(self, st):
        if st == Qt.ApplicationActive and not self.isMinimized():
            self.stage.bg.start()
        else:
            self.stage.bg.stop()

    def changeEvent(self, e):
        if self.isMinimized():
            self.stage.bg.stop()
        super().changeEvent(e)

    def say(self, msg: str, level: str = "info"):
        ts = time.strftime("%H:%M:%S")
        self.log_view.append(f'<span style="color:{theme.MUTED}">{ts}</span> '
                             f'<span style="color:{LEVEL_COLOR.get(level, theme.LILAC)}">{html.escape(msg)}</span>')
        self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())
        try:
            from ..paths import data_dir
            with open(data_dir() / "unified.log", "a", encoding="utf-8") as fh:
                fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} [{level}] {msg}\n")
        except Exception:
            pass

    def _boot(self):
        lines = [(f"› {APP_NAME} v{__version__} ready", "info"),
                 ("› โหมด UNLIMITED = ไม้ (bat) · โหมด PRO = มีด (knife) — ตั้งค่าแยกกันสมบูรณ์", "dim"),
                 ("› กดการ์ดโหมดที่ต้องการ แล้วยืนยัน — Reset เพื่อคืนค่าเดิม", "dim")]
        for i, (m, l) in enumerate(lines):
            QTimer.singleShot(250 + i * 380, lambda m=m, l=l: self.say(m, l))

    def _integrity(self, ok: bool, msg: str):
        if ok:
            self.integ.setText("ORIGINAL FILES  ·  VERIFIED ✓"); self.integ.setStyleSheet(f"color:{theme.OK};")
            self.say("Original files verified (SHA-256) - unchanged.", "ok")
        else:
            self.integ.setText("ORIGINAL FILES  ·  CHANGED ✗"); self.integ.setStyleSheet(f"color:{theme.BAD};")
            self.say("Original files failed verification: " + msg, "bad")

    def refresh(self):
        su, sp = self.unl.status(), self.pro.status()
        for card, st in ((self.c_unl, su), (self.c_pro, sp)):
            if st == "active":
                card.set_state("ACTIVE", theme.OK, pulse=True)
            else:
                card.set_state("READY", theme.CYAN)
        active = [n for n, s in (("UNLIMITED", su), ("PRO", sp)) if s == "active"]
        self.pill.setText("ACTIVE MODE  ·  " + (" + ".join(active) if active else "NONE")
                          + ("  (CONFLICT)" if len(active) == 2 else ""))

    def _set_busy(self, busy: bool, what: str = ""):
        for w in (self.c_unl, self.c_pro, self.btn_reset):
            w.setEnabled(not busy)
        if busy:
            (self.c_unl if what == "unlimited" else self.c_pro).set_state("WORKING…", theme.WARN, pulse=True)
            self.pill.setText("WORKING…  PLEASE WAIT")
        else:
            self.refresh()

    def _admin_ok(self) -> bool:
        if self.demo or is_admin():
            return True
        Dialog(self, self.f, "ADMIN REQUIRED",
               "โปรแกรมนี้ต้องรันแบบ <b>Run as administrator</b> เพื่อเขียนค่าระบบ — ปิดแล้วเปิดใหม่ด้วยสิทธิ์ผู้ดูแล",
               [("OK", "primary")], accent=theme.WARN).exec()
        return False

    def _run(self, mode_key: str, fn):
        self._set_busy(True, mode_key)
        self.worker = Worker(fn)
        self.worker.log.connect(self.say)
        self.worker.done.connect(self._finished)
        self.worker.start()

    def _finished(self, res: Result):
        self._set_busy(False)
        lvl = "ok" if res.ok else "bad"
        if res.noop:
            lvl = "warn"
        self.say(f"{res.title}: {res.summary}", lvl)
        for d in res.details:
            self.say("  · " + d, "dim")
        body = html.escape(res.summary)
        if res.details:
            body += "<ul>" + "".join(f"<li>{html.escape(d)}</li>" for d in res.details) + "</ul>"
        if res.ok and res.restart:
            body += "<p><b>แนะนำ:</b> รีสตาร์ทเครื่องเพื่อให้ค่าทั้งหมดมีผลเต็มที่ (ไม่ได้รีสตาร์ทให้อัตโนมัติ)</p>"
        Dialog(self, self.f, ("DONE · " if res.ok else "ATTENTION · ") + res.title, body,
               [("OK", "primary")], accent=theme.OK if res.ok else theme.BAD).exec()

    # ---- actions -------------------------------------------------------------------------
    def on_mode(self, key: str):
        if self.worker and self.worker.isRunning():
            return
        if not self._admin_ok():
            return
        other = self.pro if key == "unlimited" else self.unl
        other_name = "PRO" if key == "unlimited" else "UNLIMITED"
        this_name = "UNLIMITED" if key == "unlimited" else "PRO"
        reset_other = False
        if other.status() == "active":
            d = Dialog(self, self.f, f"{other_name} IS ACTIVE",
                       f"<b>{other_name}</b> ยังเปิดใช้งานอยู่ — เพื่อไม่ให้ค่าทับกัน ต้องคืนค่า {other_name} ก่อน "
                       f"แล้วจึงใช้ {this_name}<br>การรีเซ็ตนี้คืนเฉพาะค่าของ {other_name} เท่านั้น",
                       [(f"Reset {other_name} & continue", "primary"), ("Cancel", "ghost")], accent=theme.WARN)
            d.exec()
            if d.choice != 0:
                return
            reset_other = True

        if key == "unlimited":
            body = ("จะรันสคริปต์ <b>BANNARAKX_ULTIMATE.ps1</b> ต้นฉบับ (ไม่แก้ไฟล์) — DNS, Registry เน็ต, Game Mode, "
                    "เมาส์/คีย์บอร์ด, ปิด Service/Task ที่ไม่จำเป็น, ล้าง Disk Cleanup<br><br>"
                    "• หน้าต่างคอนโซลจะเด้งขึ้นมาแสดงความคืบหน้า <b>อย่าปิด</b><br>"
                    "• สคริปต์สำรองค่าเดิมให้ก่อนเสมอ (Reset คืนได้ ยกเว้น Disk Cleanup)<br>"
                    "• ไม่ปิด Defender / Firewall / Windows Update และไม่รีสตาร์ทให้เอง")
            d = Dialog(self, self.f, "APPLY · UNLIMITED (BAT)", body,
                       [("Apply", "primary"), ("Cancel", "ghost")])
            d.exec()
            if d.choice != 0:
                return
            self._run("unlimited", lambda log: self._chain(reset_other, self.pro, log, lambda: self.unl.apply(log)))
        else:
            mx = select("max"); sf = select("safe")
            lst = "".join(f"<li>{html.escape(t.title)}</li>" for t in sf)
            lst_max = "".join(f"<li>{html.escape(t.title)}</li>" for t in mx if t.level == "max")
            body = (f"<b>SAFE</b> — ปลอดภัย ทุกเครื่อง<ul>{lst}</ul>"
                    f"<b>MAX</b> — ระดับสูงสุด เฉพาะ Pro (มีด) เท่านั้น<ul>{lst_max}</ul>"
                    "ทุกค่าสำรองก่อนแก้ และ Reset คืนให้ครบ ไม่ปิด Defender / Firewall / mitigation")
            if self.pro.has_original():
                body += ("<br><br>จากนั้นเปิด <b>BANNARAKX PRO.exe</b> ต้นฉบับให้ — "
                         f"<span style='color:{theme.WARN}'>อย่ากดตัวเลือก “Security mitigations off” ในนั้น</span>")
            d = Dialog(self, self.f, "APPLY · PRO (KNIFE)", body,
                       [("Apply", "primary"), ("Cancel", "ghost")], checkbox="เปิดระดับ MAX (แนะนำ)", checked=True,
                       accent=theme.MAGENTA)
            d.exec()
            if d.choice != 0:
                return
            preset = "max" if d.cb and d.cb.isChecked() else "safe"
            self._run("pro", lambda log: self._chain(reset_other, self.unl, log, lambda: self.pro.apply(preset, log)))

    @staticmethod
    def _chain(reset_other: bool, other, log, then):
        if reset_other:
            r = other.reset(log)
            if not r.ok:
                return Result(False, "RESET FIRST", "ไม่สามารถคืนค่าโหมดเดิมได้ จึงยังไม่ได้ใช้โหมดใหม่ (กันค่าทับกัน)",
                              [r.summary] + r.details)
        return then()

    def on_reset(self):
        if self.worker and self.worker.isRunning():
            return
        su, sp = self.unl.status() == "active", self.pro.status() == "active"
        if not self._admin_ok():
            return
        state = lambda a: "ACTIVE" if a else "not active"
        d = Dialog(self, self.f, "RESET",
                   "เลือกโหมดที่จะคืนค่าเดิม — แต่ละโหมดรีเซ็ตแยกกัน ไม่กระทบอีกโหมด<br><br>"
                   f"UNLIMITED: <b>{state(su)}</b><br>PRO: <b>{state(sp)}</b>",
                   [("Reset UNLIMITED", "danger"), ("Reset PRO", "danger"), ("Cancel", "ghost")],
                   disabled={i for i, a in ((0, su), (1, sp)) if not a}, accent=theme.BAD)
        d.exec()
        if d.choice == 0:
            self._run("unlimited", lambda log: self.unl.reset(log))
        elif d.choice == 1:
            self._run("pro", lambda log: self.pro.reset(log))

    def closeEvent(self, e):
        if self.worker and self.worker.isRunning():
            Dialog(self, self.f, "WORKING", "กำลังทำงานอยู่ — รอให้เสร็จก่อนปิดโปรแกรม",
                   [("OK", "primary")], accent=theme.WARN).exec()
            e.ignore()
            return
        self.stage.bg.stop()
        super().closeEvent(e)
