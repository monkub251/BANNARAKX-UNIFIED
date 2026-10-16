"""UNLIMITED mode (bat): runs the ORIGINAL BANNARAKX_ULTIMATE.ps1 untouched.

Apply : -Auto -NoReboot          (the script saves its own backup first)
Reset : menu choice R via stdin   (the script restores from its own backup)
We only *read* its backup folder to verify the outcome."""
from __future__ import annotations

import glob
import os
import subprocess
from pathlib import Path

from . import integrity
from .common import Log, Result
from .paths import IS_WINDOWS, netforge_dir, originals_dir

PS1 = "unlimited/BANNARAKX_ULTIMATE.ps1"


def _real_runner(ps1: Path, args: list[str], stdin: bytes, timeout: int = 3600) -> int:
    cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1), *args]
    flags = 0x00000010 if IS_WINDOWS else 0  # CREATE_NEW_CONSOLE: user can watch progress
    p = subprocess.Popen(cmd, cwd=str(ps1.parent), stdin=subprocess.PIPE, creationflags=flags)
    try:
        p.communicate(input=stdin, timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        raise
    return p.returncode


class UnlimitedMode:
    key = "unlimited"

    def __init__(self, runner=_real_runner, originals: Path | None = None,
                 backup_dir: Path | None = None, verify: bool = True):
        self.runner = runner
        self.originals = Path(originals) if originals else originals_dir()
        self.backup_dir = Path(backup_dir) if backup_dir else netforge_dir()
        self.verify = verify

    @property
    def backup(self) -> Path:
        return self.backup_dir / "ultimate_backup.json"

    def _restored_count(self) -> int:
        return len(glob.glob(str(self.backup_dir / "ultimate_backup.restored.*.json")))

    def status(self) -> str:
        return "active" if self.backup.exists() else "ready"

    def _check(self, title: str) -> Result | None:
        if self.verify:
            ok, problems = integrity.verify("unlimited/", self.originals)
            if not ok:
                return Result(False, title, "Original Unlimited files failed the integrity check - nothing was run.", problems)
        return None

    def apply(self, log: Log) -> Result:
        title = "UNLIMITED"
        bad = self._check(title)
        if bad:
            return bad
        ps1 = self.originals / PS1
        log("Running the original ULTIMATE script (a console window will show its progress)...", "info")
        try:
            code = self.runner(ps1, ["-Auto", "-NoReboot"], b"\r\n\r\n")
        except Exception as e:
            return Result(False, title, "The original script could not finish.", [str(e)])
        if not self.backup.exists():
            return Result(False, title, "The script ended but did not create its safety backup, so nothing is marked active.",
                          [f"exit code {code}", f"expected: {self.backup}"])
        log("Original script finished; its own backup is in place.", "ok")
        return Result(True, title, "Unlimited applied. Safety backup verified.",
                      [f"script exit code {code}"] if code else [], restart=True)

    def reset(self, log: Log) -> Result:
        title = "UNLIMITED RESET"
        if not self.backup.exists():
            return Result(True, title, "Unlimited is not active - nothing to reset.", noop=True)
        bad = self._check(title)
        if bad:
            return bad
        before = self._restored_count()
        ps1 = self.originals / PS1
        log("Asking the original script to restore its saved values...", "info")
        try:
            code = self.runner(ps1, ["-NoReboot"], b"R\r\n\r\n\r\n")
        except Exception as e:
            return Result(False, title, "The restore could not finish. Backup kept.", [str(e)])
        if self.backup.exists() or self._restored_count() <= before:
            return Result(False, title, "The script did not confirm the restore, so it is NOT reported as restored. Backup kept.",
                          [f"exit code {code}", "check the script's console/log in ProgramData\\BannarakxNetForge"])
        log("Restore confirmed (script archived its backup).", "ok")
        return Result(True, title, "Unlimited restored. The script confirmed and archived its backup.",
                      ["Disk Cleanup (deleted temp files) cannot be undone - that is by design of the original."],
                      restart=True)
