from __future__ import annotations

import tempfile
from pathlib import Path

from .mode_pro import ProMode
from .mode_unlimited import UnlimitedMode


def build(demo: bool):
    if not demo:
        from .power import WinPower
        from .regbackend import WinRegBackend
        return UnlimitedMode(), ProMode(WinRegBackend(), WinPower())
    # DEMO: simulated registry / power / script runner - touches nothing on the machine
    from .power import MemoryPower
    from .regbackend import MemoryRegBackend
    tmp = Path(tempfile.mkdtemp(prefix="bx_demo_"))
    import time

    def fake_runner(ps1, args, stdin, timeout=0):
        time.sleep(1.2)
        b = tmp / "ultimate_backup.json"
        if "-Auto" in args:
            b.write_text("{}")
        else:
            b.unlink(missing_ok=True)
            (tmp / f"ultimate_backup.restored.{int(time.time()*1000)}.json").write_text("{}")
        return 0

    return (UnlimitedMode(runner=fake_runner, backup_dir=tmp, verify=False),
            ProMode(MemoryRegBackend(), MemoryPower(), data=tmp, verify=False,
                    launcher=lambda exe: 0))
