from pathlib import Path
import os, sys, shutil

APP_NAME = "Discovery Assistant"

def policy_dir() -> Path:
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / APP_NAME / "policy"
    elif sys.platform.startswith("win"):
        base = Path.home() / "AppData" / "Local" / APP_NAME / "policy"
    else:
        base = Path.home() / f".{APP_NAME.lower().replace(' ', '_')}" / "policy"
    base.mkdir(parents=True, exist_ok=True)
    return base

def policy_path() -> Path:
    return policy_dir() / "governance.pol"

def install_policy_from(src: Path) -> Path:
    """Copy a policy file into the canonical location and make it read-only (best-effort)."""
    dst = policy_path()
    shutil.copy2(src, dst)
    try: dst.chmod(0o444)
    except Exception: pass
    return dst

def remove_policy() -> None:
    p = policy_path()
    if p.exists():
        try: p.chmod(0o666)
        except Exception: pass
        p.unlink()

def policy_exists() -> bool:
    return policy_path().exists()

def open_policy_folder() -> None:
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtCore import QUrl
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(policy_dir())))
