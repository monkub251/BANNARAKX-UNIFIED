from __future__ import annotations

import ctypes
import os
from dataclasses import dataclass, field
from typing import Callable

# log(message, level)  level: info | ok | warn | bad | dim
Log = Callable[[str, str], None]


@dataclass
class Result:
    ok: bool
    title: str
    summary: str
    details: list[str] = field(default_factory=list)
    restart: bool = False
    noop: bool = False


def is_admin() -> bool:
    if os.name != "nt":
        return os.geteuid() == 0
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False
