#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import venv
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
APP_FILE = APP_DIR / "app.py"
REQUIREMENTS_FILE = APP_DIR / "requirements.txt"
PRIMARY_VENV_DIR = APP_DIR / ".venv"
LEGACY_VENV_DIR = APP_DIR / "venv"
CORE_IMPORTS = ("customtkinter", "cv2", "ultralytics", "PIL")


def get_venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while True:
            chunk = file.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def run_checked(cmd: list[str]) -> None:
    env = os.environ.copy()
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    subprocess.check_call(cmd, cwd=str(APP_DIR), env=env)


def is_valid_venv(venv_dir: Path) -> bool:
    python_bin = get_venv_python(venv_dir)
    if not python_bin.exists():
        return False
    check = subprocess.run([str(python_bin), "--version"], cwd=str(APP_DIR), capture_output=True, text=True)
    return check.returncode == 0


def select_or_create_venv() -> tuple[Path, Path]:
    for candidate in (PRIMARY_VENV_DIR, LEGACY_VENV_DIR):
        if is_valid_venv(candidate):
            return candidate, get_venv_python(candidate)

    venv_dir = PRIMARY_VENV_DIR
    python_bin = get_venv_python(venv_dir)
    print(f"[setup] Creating virtual environment: {venv_dir}")
    builder = venv.EnvBuilder(with_pip=True, upgrade_deps=False)
    builder.create(str(venv_dir))
    if not python_bin.exists():
        raise RuntimeError(f"Python executable not found in virtual environment: {python_bin}")
    return venv_dir, python_bin


def core_imports_ok(python_bin: Path) -> bool:
    import_stmt = "; ".join([f"import {name}" for name in CORE_IMPORTS])
    check = subprocess.run([str(python_bin), "-c", import_stmt], cwd=str(APP_DIR), capture_output=True, text=True)
    return check.returncode == 0


def ensure_dependencies(venv_dir: Path, python_bin: Path) -> None:
    if not REQUIREMENTS_FILE.exists():
        return

    req_stamp_file = venv_dir / ".requirements.sha256"
    wanted_hash = sha256_file(REQUIREMENTS_FILE)
    current_hash = req_stamp_file.read_text(encoding="utf-8").strip() if req_stamp_file.exists() else ""
    if current_hash == wanted_hash and core_imports_ok(python_bin):
        return

    print("[setup] Installing/updating dependencies from requirements.txt")
    run_checked([str(python_bin), "-m", "pip", "install", "--upgrade", "pip"])
    run_checked([str(python_bin), "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)])
    req_stamp_file.write_text(wanted_hash, encoding="utf-8")


def main() -> int:
    os.chdir(APP_DIR)

    if sys.version_info < (3, 10):
        print("[error] Please run with Python 3.10 or newer.", file=sys.stderr)
        return 1

    if not APP_FILE.exists():
        print(f"[error] app.py not found at: {APP_FILE}", file=sys.stderr)
        return 1

    venv_dir, python_bin = select_or_create_venv()
    ensure_dependencies(venv_dir, python_bin)

    cmd = [str(python_bin), str(APP_FILE), *sys.argv[1:]]
    return subprocess.call(cmd, cwd=str(APP_DIR))


if __name__ == "__main__":
    raise SystemExit(main())
