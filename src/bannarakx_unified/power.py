from __future__ import annotations

import re
import subprocess

from .paths import IS_WINDOWS

HIGH_PERFORMANCE = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
_GUID = re.compile(r"([0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12})")


class WinPower:
    def _run(self, *args: str) -> str:
        flags = 0x08000000 if IS_WINDOWS else 0  # CREATE_NO_WINDOW
        r = subprocess.run(["powercfg", *args], capture_output=True, text=True,
                           timeout=20, creationflags=flags)
        if r.returncode != 0:
            raise RuntimeError((r.stderr or r.stdout).strip() or f"powercfg exit {r.returncode}")
        return r.stdout

    def get_active(self) -> str | None:
        m = _GUID.search(self._run("/getactivescheme"))
        return m.group(1).lower() if m else None

    def exists(self, guid: str) -> bool:
        return guid.lower() in self._run("/list").lower()

    def set_active(self, guid: str) -> None:
        self._run("/setactive", guid)


class MemoryPower:
    def __init__(self, active: str = "381b4222-f694-41f0-9685-ff5bb260df2e", available=(HIGH_PERFORMANCE,)):
        self.active = active
        self.available = {a.lower() for a in available} | {active.lower()}

    def get_active(self):
        return self.active

    def exists(self, guid):
        return guid.lower() in self.available

    def set_active(self, guid):
        if guid.lower() not in self.available:
            raise RuntimeError("plan not found")
        self.active = guid.lower()
