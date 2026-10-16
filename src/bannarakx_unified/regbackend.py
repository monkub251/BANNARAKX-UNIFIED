"""Registry access behind a tiny interface so the logic is testable off-Windows."""
from __future__ import annotations

from typing import Any, Protocol

Value = tuple[str, Any]  # (type_name, jsonable value)


class RegBackend(Protocol):
    def read(self, hive: str, path: str, name: str) -> Value | None: ...
    def write(self, hive: str, path: str, name: str, type_name: str, value: Any) -> None: ...
    def delete(self, hive: str, path: str, name: str) -> None: ...


class WinRegBackend:
    def __init__(self) -> None:
        import winreg  # Windows only

        self.w = winreg
        self.hives = {"HKCU": winreg.HKEY_CURRENT_USER, "HKLM": winreg.HKEY_LOCAL_MACHINE}
        self.types = {
            "DWORD": winreg.REG_DWORD, "SZ": winreg.REG_SZ, "EXPAND_SZ": winreg.REG_EXPAND_SZ,
            "BINARY": winreg.REG_BINARY, "QWORD": winreg.REG_QWORD, "MULTI_SZ": winreg.REG_MULTI_SZ,
        }
        self.names = {v: k for k, v in self.types.items()}

    def read(self, hive, path, name):
        w = self.w
        try:
            with w.OpenKey(self.hives[hive], path, 0, w.KEY_READ | w.KEY_WOW64_64KEY) as k:
                v, t = w.QueryValueEx(k, name)
        except FileNotFoundError:
            return None
        tn = self.names.get(t, "SZ")
        if tn == "BINARY":
            v = bytes(v).hex()
        return tn, v

    def write(self, hive, path, name, type_name, value):
        w = self.w
        if type_name == "BINARY":
            value = bytes.fromhex(value)
        with w.CreateKeyEx(self.hives[hive], path, 0, w.KEY_SET_VALUE | w.KEY_WOW64_64KEY) as k:
            w.SetValueEx(k, name, 0, self.types[type_name], value)

    def delete(self, hive, path, name):
        w = self.w
        try:
            with w.OpenKey(self.hives[hive], path, 0, w.KEY_SET_VALUE | w.KEY_WOW64_64KEY) as k:
                w.DeleteValue(k, name)
        except FileNotFoundError:
            pass


class MemoryRegBackend:
    """In-memory registry for tests and --demo. `fail_write` injects failures."""

    def __init__(self, initial: dict | None = None) -> None:
        self.data: dict[tuple[str, str, str], Value] = dict(initial or {})
        self.fail_write: set[str] = set()

    def read(self, hive, path, name):
        return self.data.get((hive, path.lower(), name.lower()))

    def write(self, hive, path, name, type_name, value):
        if name in self.fail_write:
            raise PermissionError(f"access denied: {name}")
        self.data[(hive, path.lower(), name.lower())] = (type_name, value)

    def delete(self, hive, path, name):
        if name in self.fail_write:
            raise PermissionError(f"access denied: {name}")
        self.data.pop((hive, path.lower(), name.lower()), None)
