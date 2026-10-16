from __future__ import annotations

from PySide6.QtGui import QFontDatabase

BG = "#06040e"
PANEL = "#0c0919"
LINE = "#2b2150"
VIOLET = "#8b5cf6"
LILAC = "#c4b5fd"
MAGENTA = "#d946ef"
CYAN = "#22d3ee"
OK = "#4ade80"
WARN = "#fbbf24"
BAD = "#fb7185"
TEXT = "#ece8ff"
MUTED = "#8c84b4"

DISPLAY = ["Bahnschrift", "Segoe UI Variable Display", "Segoe UI Semibold", "Segoe UI", "Inter", "DejaVu Sans"]
MONO = ["Cascadia Mono", "Cascadia Code", "Consolas", "JetBrains Mono", "DejaVu Sans Mono"]
BODY = ["Segoe UI Variable Text", "Segoe UI", "Leelawadee UI", "Tahoma", "DejaVu Sans"]


def pick(cands: list[str]) -> str:
    have = set(QFontDatabase.families())
    for c in cands:
        if c in have:
            return c
    return cands[-1]


class Fonts:
    def __init__(self) -> None:
        self.display = pick(DISPLAY)
        self.mono = pick(MONO)
        self.body = pick(BODY)


def stylesheet(f: Fonts) -> str:
    return f"""
    QWidget {{ color: {TEXT}; font-family: '{f.body}'; font-size: 13px; }}
    QDialog {{ background: {PANEL}; }}
    QLabel {{ background: transparent; }}
    QTextEdit#log {{ background: rgba(8,6,18,215); border: 1px solid {LINE}; border-radius: 12px;
        padding: 8px 10px; font-family: '{f.mono}'; font-size: 12px; selection-background-color: {VIOLET}; }}
    QPushButton[variant="primary"] {{ background: {VIOLET}; color: white; border: none; border-radius: 10px;
        padding: 10px 22px; font-family: '{f.display}'; font-weight: 600; letter-spacing: 1px; }}
    QPushButton[variant="primary"]:hover {{ background: #9d75f8; }}
    QPushButton[variant="ghost"] {{ background: rgba(255,255,255,0.03); color: {LILAC}; border: 1px solid {LINE};
        border-radius: 10px; padding: 10px 22px; font-family: '{f.display}'; font-weight: 600; letter-spacing: 1px; }}
    QPushButton[variant="ghost"]:hover {{ border-color: {VIOLET}; background: rgba(139,92,246,0.12); }}
    QPushButton[variant="danger"] {{ background: rgba(251,113,133,0.10); color: {BAD}; border: 1px solid rgba(251,113,133,0.5);
        border-radius: 10px; padding: 10px 22px; font-family: '{f.display}'; font-weight: 600; letter-spacing: 1px; }}
    QPushButton[variant="danger"]:hover {{ background: rgba(251,113,133,0.22); }}
    QPushButton:disabled {{ color: #5b5480; border-color: #231b44; background: rgba(255,255,255,0.02); }}
    QCheckBox {{ spacing: 8px; }}
    QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px; border: 1px solid {LINE}; background: #120d26; }}
    QCheckBox::indicator:checked {{ background: {VIOLET}; border-color: {VIOLET}; }}
    QScrollBar:vertical {{ background: transparent; width: 8px; }}
    QScrollBar::handle:vertical {{ background: {LINE}; border-radius: 4px; min-height: 24px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    """
