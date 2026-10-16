from __future__ import annotations

import sys

from . import APP_NAME, __version__


def _relaunch_as_admin() -> bool:
    import ctypes
    if getattr(sys, "frozen", False):
        exe, params = sys.executable, " ".join(f'"{a}"' for a in sys.argv[1:])
    else:
        exe, params = sys.executable, " ".join(f'"{a}"' for a in ["-m", "bannarakx_unified", *sys.argv[1:]])
    return ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1) > 32


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--version" in argv:
        print(f"{APP_NAME} {__version__}")
        return 0
    demo = "--demo" in argv
    from .common import is_admin
    from .paths import IS_WINDOWS
    if IS_WINDOWS and not demo and "--no-admin" not in argv and not is_admin():
        if _relaunch_as_admin():
            return 0

    from PySide6.QtCore import QPropertyAnimation
    from PySide6.QtWidgets import QApplication, QMessageBox

    app = QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    from .ui import theme
    fonts = theme.Fonts()
    app.setStyleSheet(theme.stylesheet(fonts))
    try:
        from .services import build
        unl, pro = build(demo)
    except Exception as e:
        QMessageBox.critical(None, APP_NAME, f"Could not start:\n{e}")
        return 1
    from .ui.window import MainWindow
    w = MainWindow(unl, pro, fonts, demo)
    w.setWindowOpacity(0.0)
    w.show()
    fade = QPropertyAnimation(w, b"windowOpacity", w)
    fade.setDuration(450); fade.setStartValue(0.0); fade.setEndValue(1.0); fade.start()
    w._fade = fade
    return app.exec()
