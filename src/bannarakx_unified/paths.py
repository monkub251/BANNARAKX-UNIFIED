"""All filesystem locations in one place (override with env vars for tests)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

IS_WINDOWS = os.name == "nt"


def app_dir() -> Path:
    """Folder that holds the .exe (or the repo root when running from source)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def assets_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", app_dir())) / "assets"
    return app_dir() / "assets"


def originals_dir() -> Path:
    return Path(os.environ.get("BANNARAKX_ORIGINALS", app_dir() / "originals"))


def _program_data() -> Path:
    if IS_WINDOWS:
        return Path(os.environ.get("ProgramData", r"C:\ProgramData"))
    return Path.home() / ".bannarakx_unified"


def data_dir() -> Path:
    """Our own data (Pro snapshot + log). Never shared with the original tools."""
    d = Path(os.environ.get("BANNARAKX_DATA", _program_data() / "BannarakxUnified"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def netforge_dir() -> Path:
    """Where the ORIGINAL Unlimited script keeps its own backup (we only read it)."""
    return Path(os.environ.get("BANNARAKX_NETFORGE_DIR", _program_data() / "BannarakxNetForge"))
