"""Regenerate originals/MANIFEST.json (run only when you INTENTIONALLY replace an original)."""
import hashlib, json, sys
from pathlib import Path

base = Path(__file__).resolve().parents[1] / "originals"
files = {}
for p in sorted(base.rglob("*")):
    if p.is_file() and p.name != "MANIFEST.json":
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for c in iter(lambda: f.read(1 << 20), b""):
                h.update(c)
        files[p.relative_to(base).as_posix()] = h.hexdigest()
(base / "MANIFEST.json").write_text(json.dumps({"files": files}, indent=1), encoding="utf-8")
print(f"{len(files)} files hashed -> {base / 'MANIFEST.json'}")
