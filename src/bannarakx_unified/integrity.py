"""Proves the original files were not modified (SHA-256 manifest)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .paths import originals_dir


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(base: Path | None = None) -> dict[str, str]:
    base = base or originals_dir()
    mf = base / "MANIFEST.json"
    with open(mf, "r", encoding="utf-8") as f:
        return json.load(f)["files"]


def verify(prefix: str, base: Path | None = None) -> tuple[bool, list[str]]:
    """Check every manifest entry under `prefix` ('unlimited/' or 'pro/')."""
    base = base or originals_dir()
    try:
        files = load_manifest(base)
    except Exception as e:  # missing / corrupt manifest
        return False, [f"manifest unreadable: {e}"]
    problems: list[str] = []
    seen = 0
    for rel, want in files.items():
        if not rel.startswith(prefix):
            continue
        seen += 1
        p = base / rel
        if not p.is_file():
            problems.append(f"missing: {rel}")
        elif sha256(p) != want:
            problems.append(f"modified: {rel}")
    if seen == 0:
        problems.append(f"no manifest entries for {prefix}")
    return (not problems), problems
