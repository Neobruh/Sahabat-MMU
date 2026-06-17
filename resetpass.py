"""
Resets admin_demo's password back to adminpass123.
Run from your project folder: python reset_admin_password.py
"""

import sqlite3, os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance", "sahabat.db")
if not os.path.exists(DB_PATH):
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sahabat.db")

USERNAME     = "admin_demo"
NEW_PASSWORD = "adminpass123"

def run():
    if not os.path.exists(DB_PATH):
        print(f"❌  Database not found at: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    hashed = generate_password_hash(NEW_PASSWORD)
    cur.execute("UPDATE users SET password_hash = ? WHERE username = ?", (hashed, USERNAME))

    if cur.rowcount == 0:
        print(f"❌  No user found with username '{USERNAME}'. Check the username and try again.")
    else:
        print(f"✅  Password for '{USERNAME}' reset to '{NEW_PASSWORD}' successfully.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    run()