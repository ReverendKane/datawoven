"""
PACKAGING NOTE (run this before zipping/packaging for a client):
- Prompts for a new admin password and writes the hashed credentials file.
- Lives at project_root, imports your library code.

In your spec file when creating the executable (app, exe) you are going to want to
include excludes=['set_password'] in the .spec file if needed. make sure you work this
out before distributing

Typical use:
    python set_password.py
"""
from getpass import getpass
from discovery_assistant.admin_auth import set_admin_password, _creds_path

def main():
    print("=== Discovery Assistant Admin Password Setup ===")
    pwd1 = getpass("Enter new admin password: ")
    pwd2 = getpass("Re-enter password: ")
    if pwd1 != pwd2:
        print("❌ Passwords do not match.")
        return
    set_admin_password(pwd1, must_change=False)
    print(f"✅ Admin password set. Credentials stored at: {_creds_path()}")

if __name__ == "__main__":
    main()
