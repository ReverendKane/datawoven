"""
ADMIN AUTH
----------
This module stores & verifies the Admin password. It also supports a
'first login must change password' flow for safer client handoffs.

PACKAGING NOTE (when preparing a client build):
1) Generate a strong temp password:
       from discovery_assistant.admin_auth import generate_temp_password, set_admin_password
       tmp = generate_temp_password()
       print("TEMP ADMIN PASSWORD:", tmp)   # give to client admin
       set_admin_password(tmp, must_change=True)
2) Ship the app. On first admin login, they'll be forced to set a new password.
"""

from pathlib import Path
import os, sys, json, base64, hashlib, secrets

APP_NAME = "Discovery Assistant"

def _canon_policy_dir() -> Path:
    if os.name == "nt":
        base = Path.home() / "AppData" / "Local" / APP_NAME / "policy"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / APP_NAME / "policy"
    else:
        base = Path.home() / f".{APP_NAME.lower().replace(' ', '_')}" / "policy"
    base.mkdir(parents=True, exist_ok=True)
    return base

def _creds_path() -> Path:
    # Keep admin_config.json next to policy/, one level up
    return _canon_policy_dir().parent / "admin_config.json"

def _pbkdf2_hash(pwd: str, salt: bytes, rounds: int = 100_000) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", pwd.encode("utf-8"), salt, rounds)
    return base64.b64encode(dk).decode("utf-8")

def _write_creds(data: dict) -> None:
    _creds_path().write_text(json.dumps(data), encoding="utf-8")

def _read_creds() -> dict:
    p = _creds_path()
    if not p.exists():
        # Bootstrap default for dev; during packaging you will overwrite this via set_admin_password(...)
        set_admin_password("admin123", must_change=True)
    return json.loads(_creds_path().read_text(encoding="utf-8"))

def set_admin_password(new_password: str, *, must_change: bool = False) -> str:
    """Create/update the admin password. Call this during packaging for each client."""
    salt = os.urandom(16)
    h = _pbkdf2_hash(new_password, salt)
    data = {
        "algo": "pbkdf2_sha256",
        "rounds": 100000,
        "salt": base64.b64encode(salt).decode("utf-8"),
        "hash": h,
        "must_change": bool(must_change)
    }
    _write_creds(data)
    return "admin password updated"

def change_admin_password(old_password: str, new_password: str) -> bool:
    """Used by the 'must change' dialog after first login."""
    data = _read_creds()
    salt = base64.b64decode(data["salt"].encode("utf-8"))
    if _pbkdf2_hash(old_password, salt, data.get("rounds", 100_000)) != data["hash"]:
        return False
    set_admin_password(new_password, must_change=False)
    return True

class VerifyResult:
    OK = "ok"
    OK_MUST_CHANGE = "ok_must_change"
    FAIL = "fail"

def verify_admin_password(pwd: str) -> str:
    data = _read_creds()
    salt = base64.b64decode(data["salt"].encode("utf-8"))
    ok = _pbkdf2_hash(pwd, salt, data.get("rounds", 100_000)) == data["hash"]
    if not ok:
        return VerifyResult.FAIL
    return VerifyResult.OK_MUST_CHANGE if data.get("must_change") else VerifyResult.OK

def generate_temp_password(length: int = 20) -> str:
    """Convenience for packaging: generate a random admin temp password."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789-_.@"
    return "".join(secrets.choice(alphabet) for _ in range(length))
