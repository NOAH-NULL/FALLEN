"""Build a deterministic source release without local build/runtime artifacts."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist"
NAME = "Fallen-v1.0-performance-first.zip"
EXCLUDED_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "htmlcov", "dist"}
EXCLUDED_FILES = {".coverage", "*.pyc"}


def ignored(path: Path) -> bool:
    parts = set(path.relative_to(ROOT).parts)
    if parts & EXCLUDED_DIRS:
        return True
    return path.name == ".coverage" or path.suffix == ".pyc"


def main() -> int:
    OUT.mkdir(exist_ok=True)
    target = OUT / NAME
    with tempfile.TemporaryDirectory(prefix="fallen-release-") as tmp:
        staging = Path(tmp) / "fallen"
        for src in ROOT.iterdir():
            if src.name in {"dist", ".git", ".venv", "venv", ".pytest_cache", "htmlcov"}:
                continue
            dst = staging / src.name
            if src.is_dir():
                shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc", ".coverage"))
            elif not ignored(src):
                shutil.copy2(src, dst)

        subprocess.run([sys.executable, "-m", "compileall", "-q", "-f", str(staging / "bot")], check=True)
        # Compile validation creates bytecode; remove it before packaging.
        for p in staging.rglob("__pycache__"):
            shutil.rmtree(p)
        for p in staging.rglob("*.pyc"):
            p.unlink()

        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(staging.rglob("*")):
                if p.is_file():
                    zf.write(p, p.relative_to(staging).as_posix())

    with zipfile.ZipFile(target) as zf:
        bad = [n for n in zf.namelist() if "__pycache__/" in n or n.endswith(".pyc") or n.endswith(".coverage")]
        if bad:
            raise RuntimeError(f"release contains forbidden artifacts: {bad}")
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
