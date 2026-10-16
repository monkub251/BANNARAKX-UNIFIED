import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from bannarakx_unified import integrity
from bannarakx_unified.mode_pro import ProMode
from bannarakx_unified.mode_unlimited import UnlimitedMode
from bannarakx_unified.power import HIGH_PERFORMANCE, MemoryPower
from bannarakx_unified.regbackend import MemoryRegBackend
from bannarakx_unified.tweaks_pro import select

LOG = lambda m, l="info": None
ORIG = Path(__file__).resolve().parents[1] / "originals"


def mk(tmp_path, reg=None, power=None):
    reg = reg or MemoryRegBackend({
        ("HKCU", r"control panel\mouse", "mousespeed"): ("SZ", "1"),          # existed
        ("HKLM", r"system\currentcontrolset\control\prioritycontrol", "win32priorityseparation"): ("DWORD", 2),
    })
    power = power or MemoryPower()
    return reg, power, ProMode(reg, power, data=tmp_path, originals=ORIG, verify=False, launcher=lambda e: 1)


def test_pro_apply_then_reset_restores_exactly(tmp_path):
    reg, power, pro = mk(tmp_path)
    before = dict(reg.data); plan = power.get_active()
    r = pro.apply("max", LOG)
    assert r.ok and pro.status() == "active"
    assert reg.read("HKCU", r"Control Panel\Mouse", "MouseSpeed") == ("SZ", "0")
    assert power.get_active() == HIGH_PERFORMANCE
    r = pro.reset(LOG)
    assert r.ok and pro.status() == "ready"
    assert reg.data == before            # values that did not exist are gone again, others back
    assert power.get_active() == plan


def test_reapply_keeps_original_snapshot(tmp_path):
    reg, power, pro = mk(tmp_path)
    before = dict(reg.data)
    pro.apply("safe", LOG); pro.apply("max", LOG); pro.apply("max", LOG)
    assert pro.reset(LOG).ok and reg.data == before


def test_safe_preset_has_no_max_tweaks(tmp_path):
    reg, power, pro = mk(tmp_path)
    pro.apply("safe", LOG)
    assert reg.read("HKLM", r"SYSTEM\CurrentControlSet\Control\PriorityControl", "Win32PrioritySeparation") == ("DWORD", 2)
    assert power.get_active() != HIGH_PERFORMANCE
    assert all(t.level == "safe" for t in select("safe"))


def test_failed_write_is_reported_and_reset_still_works(tmp_path):
    reg, power, pro = mk(tmp_path)
    before = dict(reg.data)
    reg.fail_write = {"KeyboardSpeed"}
    r = pro.apply("max", LOG)
    assert not r.ok and any("Fastest key repeat" in d for d in r.details)
    reg.fail_write = set()
    assert pro.reset(LOG).ok and reg.data == before


def test_reset_failure_is_not_reported_as_restored(tmp_path):
    reg, power, pro = mk(tmp_path)
    pro.apply("max", LOG)
    reg.fail_write = {"MouseSpeed"}
    r = pro.reset(LOG)
    assert not r.ok and pro.status() == "active"      # backup kept, no false claim


def test_nothing_applied_means_not_active(tmp_path):
    reg = MemoryRegBackend(); reg.fail_write = {t.items[0].name for t in select("max") if t.items}
    reg.fail_write |= {i.name for t in select("max") for i in t.items}
    power = MemoryPower(available=())
    _, _, pro = mk(tmp_path, reg, power)
    assert not pro.apply("max", LOG).ok and pro.status() == "ready"


def test_unavailable_power_plan_is_skipped_not_failed(tmp_path):
    reg, power, pro = mk(tmp_path, power=MemoryPower(available=()))
    r = pro.apply("max", LOG)
    assert r.ok and any("skipped" in d for d in r.details)


def test_reset_when_inactive_is_noop(tmp_path):
    _, _, pro = mk(tmp_path)
    r = pro.reset(LOG)
    assert r.ok and r.noop


def test_pro_reset_never_touches_unlimited_backup(tmp_path):
    reg, power, pro = mk(tmp_path)
    ub = tmp_path / "ultimate_backup.json"; ub.write_text("{}")
    pro.apply("max", LOG); pro.reset(LOG)
    assert ub.read_text() == "{}"


def fake_runner_factory(d, confirm=True):
    calls = []
    def run(ps1, args, stdin, timeout=0):
        calls.append((args, stdin))
        b = d / "ultimate_backup.json"
        if "-Auto" in args:
            b.write_text("{}")
        elif confirm:
            b.unlink(); (d / "ultimate_backup.restored.1.json").write_text("{}")
        return 0
    return run, calls


def test_unlimited_apply_reset_roundtrip(tmp_path):
    run, calls = fake_runner_factory(tmp_path)
    u = UnlimitedMode(runner=run, originals=ORIG, backup_dir=tmp_path, verify=False)
    assert u.apply(LOG).ok and u.status() == "active"
    assert calls[0][0] == ["-Auto", "-NoReboot"]
    assert u.reset(LOG).ok and u.status() == "ready"
    assert calls[1][1].startswith(b"R")


def test_unlimited_reset_unconfirmed_is_failure(tmp_path):
    run, _ = fake_runner_factory(tmp_path, confirm=False)
    u = UnlimitedMode(runner=run, originals=ORIG, backup_dir=tmp_path, verify=False)
    u.apply(LOG)
    r = u.reset(LOG)
    assert not r.ok and u.status() == "active"


def test_unlimited_without_backup_after_run_is_failure(tmp_path):
    u = UnlimitedMode(runner=lambda *a, **k: 0, originals=ORIG, backup_dir=tmp_path, verify=False)
    assert not u.apply(LOG).ok and u.status() == "ready"


def test_originals_match_manifest():
    ok, problems = integrity.verify("unlimited/", ORIG)
    assert ok, problems
    assert not (ORIG / "pro").exists()          # no binary shipped in this build


def test_tampered_original_blocks_run(tmp_path):
    import shutil
    shutil.copytree(ORIG / "unlimited", tmp_path / "unlimited")
    shutil.copy(ORIG / "MANIFEST.json", tmp_path / "MANIFEST.json")
    (tmp_path / "unlimited" / "BANNARAKX_ULTIMATE.ps1").write_bytes(b"# evil")
    called = []
    u = UnlimitedMode(runner=lambda *a, **k: called.append(1) or 0, originals=tmp_path,
                      backup_dir=tmp_path / "bk", verify=True)
    r = u.apply(LOG)
    assert not r.ok and not called and any("modified" in d for d in r.details)


def test_mode_state_files_are_separate(tmp_path):
    reg, power, pro = mk(tmp_path)
    assert pro.snap_path.name == "pro_snapshot.json"
    assert UnlimitedMode(backup_dir=tmp_path).backup.name == "ultimate_backup.json"


def test_pro_works_without_original_exe_and_never_launches_it(tmp_path):
    launched = []
    reg, power = MemoryRegBackend(), MemoryPower()
    pro = ProMode(reg, power, data=tmp_path, originals=ORIG, verify=True, launcher=lambda e: launched.append(e) or 1)
    assert not pro.has_original()
    assert pro.apply("max", LOG).ok and not launched
    assert pro.reset(LOG).ok
