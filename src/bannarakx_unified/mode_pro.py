"""PRO mode (knife): original BANNARAKX PRO.exe  +  the Pro-only MAX layer.

The MAX layer owns its own snapshot file, so Reset restores exactly what *it* changed and
nothing else. It never touches Unlimited's backup."""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

from . import integrity
from .common import Log, Result
from .paths import data_dir, originals_dir
from .power import MemoryPower
from .regbackend import RegBackend
from .tweaks_pro import select

PRO_EXE = "pro/BANNARAKX PRO.exe"


def _real_launch(exe: Path) -> int:
    p = subprocess.Popen([str(exe)], cwd=str(exe.parent))
    return p.pid


class ProMode:
    key = "pro"

    def __init__(self, reg: RegBackend, power, data: Path | None = None,
                 originals: Path | None = None, verify: bool = True, launcher=_real_launch):
        self.reg, self.power = reg, power
        self.data = Path(data) if data else data_dir()
        self.originals = Path(originals) if originals else originals_dir()
        self.verify, self.launcher = verify, launcher
        self.snap_path = self.data / "pro_snapshot.json"

    # -- state -------------------------------------------------------------------------
    def has_original(self) -> bool:
        """The original PRO.exe is OPTIONAL and is not shipped in this build."""
        return (self.originals / PRO_EXE).is_file()

    def status(self) -> str:
        return "active" if self.snap_path.exists() else "ready"

    def _load(self) -> dict | None:
        try:
            with open(self.snap_path, "r", encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, dict) and "values" in d else None
        except FileNotFoundError:
            return None

    def _save(self, snap: dict) -> None:
        self.data.mkdir(parents=True, exist_ok=True)
        tmp = self.snap_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(snap, f, indent=1)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.snap_path)

    # -- apply -------------------------------------------------------------------------
    def apply(self, preset: str, log: Log, launch: bool = True) -> Result:
        title = "PRO"
        if self.verify and self.has_original():
            ok, problems = integrity.verify("pro/", self.originals)
            if not ok:
                return Result(False, title, "The optional original PRO.exe is not in the verified manifest or was changed - nothing was changed.", problems)
        tweaks = select(preset)
        snap = self._load()
        fresh = snap is None
        if fresh:
            snap = {"version": 1, "created": time.strftime("%Y-%m-%d %H:%M:%S"), "values": {}, "power": None}
        else:
            log("Pro is already active - keeping the ORIGINAL snapshot, applying on top.", "info")
        snap["preset"] = preset

        # 1) snapshot first (write-ahead) - never overwrite an existing original value
        for t in tweaks:
            for it in t.items:
                if it.key not in snap["values"]:
                    cur = self.reg.read(it.hive, it.path, it.name)
                    snap["values"][it.key] = {"hive": it.hive, "path": it.path, "name": it.name,
                                              "existed": cur is not None,
                                              "type": cur[0] if cur else None,
                                              "value": cur[1] if cur else None}
            if t.power_plan and snap["power"] is None:
                try:
                    g = self.power.get_active()
                except Exception:
                    g = None
                if g:
                    snap["power"] = {"guid": g}
        try:
            self._save(snap)
        except Exception as e:
            return Result(False, title, "Could not save the safety backup, so NOTHING was changed.", [str(e)])
        log(f"Safety snapshot saved ({len(snap['values'])} values).", "dim")

        # 2) apply + read back every value
        okc, failed, skipped = 0, [], []
        for t in tweaks:
            try:
                if t.power_plan:
                    if not self.power.exists(t.power_plan) or snap["power"] is None:
                        skipped.append(t.title)
                        log(f"SKIP  {t.title} - not available on this PC", "warn")
                        continue
                    self.power.set_active(t.power_plan)
                    if (self.power.get_active() or "").lower() != t.power_plan:
                        raise RuntimeError("plan did not switch")
                for it in t.items:
                    self.reg.write(it.hive, it.path, it.name, it.type, it.value)
                    got = self.reg.read(it.hive, it.path, it.name)
                    if got is None or got[1] != it.value:
                        raise RuntimeError(f"read-back mismatch on {it.name}")
                okc += 1
                log(f"OK    {t.title}", "ok")
            except Exception as e:
                failed.append(f"{t.title}: {e}")
                log(f"FAIL  {t.title}: {e}", "bad")

        if okc == 0 and fresh:  # nothing changed -> do not pretend Pro is active
            try:
                self.snap_path.unlink()
            except OSError:
                pass
        else:
            self._save(snap)

        details = failed + [f"skipped: {s}" for s in skipped]
        if launch and okc and self.has_original():
            exe = self.originals / PRO_EXE
            try:
                pid = self.launcher(exe)
                log(f"Original BANNARAKX PRO.exe launched (pid {pid}).", "info")
            except Exception as e:
                details.append(f"could not launch original PRO.exe: {e}")
                log(f"Could not launch original PRO.exe: {e}", "warn")
        ok = okc > 0 and not failed
        summary = (f"{okc}/{len(tweaks)} Pro tweaks applied and verified."
                   + (f" {len(failed)} failed." if failed else "")
                   + (f" {len(skipped)} skipped (unsupported)." if skipped else ""))
        return Result(ok, title, summary, details, restart=ok)

    # -- reset -------------------------------------------------------------------------
    def reset(self, log: Log) -> Result:
        title = "PRO RESET"
        if not self.snap_path.exists():
            return Result(True, title, "Pro is not active - nothing to reset.", noop=True)
        snap = self._load()
        if snap is None:
            return Result(False, title, "The Pro backup file is unreadable. It was kept untouched.", [str(self.snap_path)])
        failed = []
        for k, v in snap["values"].items():
            try:
                if v["existed"]:
                    self.reg.write(v["hive"], v["path"], v["name"], v["type"], v["value"])
                    got = self.reg.read(v["hive"], v["path"], v["name"])
                    if got is None or got[1] != v["value"]:
                        raise RuntimeError("read-back mismatch")
                else:
                    self.reg.delete(v["hive"], v["path"], v["name"])
                    if self.reg.read(v["hive"], v["path"], v["name"]) is not None:
                        raise RuntimeError("value still present")
            except Exception as e:
                failed.append(f"{k}: {e}")
                log(f"FAIL  {v['name']}: {e}", "bad")
        if snap.get("power"):
            try:
                self.power.set_active(snap["power"]["guid"])
                if (self.power.get_active() or "").lower() != snap["power"]["guid"].lower():
                    raise RuntimeError("plan did not switch back")
            except Exception as e:
                failed.append(f"power plan: {e}")
                log(f"FAIL  power plan: {e}", "bad")
        total = len(snap["values"]) + (1 if snap.get("power") else 0)
        if failed:
            return Result(False, title,
                          f"Only {total - len(failed)}/{total} items restored. Backup kept so you can retry.", failed)
        archived = self.snap_path.with_name("pro_snapshot.restored." + time.strftime("%Y%m%d%H%M%S") + ".json")
        os.replace(self.snap_path, archived)
        log(f"{total}/{total} original values restored and verified.", "ok")
        return Result(True, title, f"{total}/{total} original values restored and verified.",
                      ["Settings made inside the original PRO.exe window are kept by that program - "
                       "use its own restore for those."], restart=True)
