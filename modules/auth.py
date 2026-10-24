"""
WattWise Authentication & Access Control System.
Provides secure password hashing (PBKDF2-HMAC-SHA256 with 600,000 iterations and 16-byte cryptographic salt),
constant-time verification, role-based authorization (User / Admin), and user account management.
"""
from pathlib import Path
import sqlite3
import hashlib
import secrets
import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

DB_PATH = Path("electricity.db")
ITERATIONS = 600000  # OWASP recommended minimum for PBKDF2-HMAC-SHA256


# =====================================================================
# CRYPTOGRAPHIC UTILITIES
# =====================================================================

def hash_password(password: str) -> str:
    """
    Hash a password using PBKDF2-HMAC-SHA256 with a unique 16-byte random salt.
    Returns: pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>
    """
    if not isinstance(password, str) or not password:
        raise ValueError("Password must be a non-empty string.")
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a candidate password against a stored PBKDF2-HMAC-SHA256 hash using constant-time comparison.
    """
    if not password or not hashed:
        return False
    try:
        parts = hashed.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_hash = bytes.fromhex(parts[3])

        candidate_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return secrets.compare_digest(candidate_hash, expected_hash)
    except Exception:
        return False


def validate_username(username: str) -> Tuple[bool, str]:
    """Validate username format and length."""
    if not username or not isinstance(username, str):
        return False, "Username cannot be empty."
    cleaned = username.strip()
    if len(cleaned) < 3:
        return False, "Username must be at least 3 characters long."
    if len(cleaned) > 30:
        return False, "Username cannot exceed 30 characters."
    if not re.match(r"^[a-zA-Z0-9_\-\.]+$", cleaned):
        return False, "Username can only contain alphanumeric characters, hyphens, dots, and underscores."
    return True, ""


def validate_password(password: str) -> Tuple[bool, str]:
    """Enforce minimum password strength rules."""
    if not password or not isinstance(password, str):
        return False, "Password cannot be empty."
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Za-z]", password):
        return False, "Password must contain at least one letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number."
    return True, ""


# =====================================================================
# DATABASE INITIALIZATION & MIGRATIONS
# =====================================================================

def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    target = db_path or DB_PATH
    conn = sqlite3.connect(str(target))
    conn.row_factory = sqlite3.Row
    return conn


def init_auth_db(db_path: Optional[Path] = None) -> None:
    """
    Ensure the users table exists and perform non-destructive schema migrations
    on energy_saving_actions to support user associations.
    """
    conn = get_connection(db_path)
    try:
        with conn:
            # 1. Create users table
            conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                last_login TEXT
            );
            """)

            # 2. Add user_id and username columns to energy_saving_actions if table exists
            tbl = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='energy_saving_actions';").fetchone()
            if tbl:
                cursor = conn.execute("PRAGMA table_info(energy_saving_actions);")
                existing_cols = {row["name"] for row in cursor.fetchall()}

                if "user_id" not in existing_cols:
                    conn.execute("ALTER TABLE energy_saving_actions ADD COLUMN user_id INTEGER;")
                if "username" not in existing_cols:
                    conn.execute("ALTER TABLE energy_saving_actions ADD COLUMN username TEXT;")
    finally:
        conn.close()


# =====================================================================
# USER & ADMIN MANAGEMENT OPERATIONS
# =====================================================================

def count_users(db_path: Optional[Path] = None) -> int:
    """Return total number of registered users."""
    init_auth_db(db_path)
    conn = get_connection(db_path)
    try:
        cur = conn.execute("SELECT COUNT(*) FROM users;")
        return cur.fetchone()[0]
    finally:
        conn.close()


def count_admins(db_path: Optional[Path] = None) -> int:
    """Return total number of active administrators."""
    init_auth_db(db_path)
    conn = get_connection(db_path)
    try:
        cur = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = 1;")
        return cur.fetchone()[0]
    finally:
        conn.close()


def register_user(
    username: str,
    password: str,
    role: str = "user",
    db_path: Optional[Path] = None,
) -> Tuple[bool, str, Optional[int]]:
    """
    Register a new user account with secure password hashing.
    Enforces username validation, password strength, and uniqueness.
    """
    init_auth_db(db_path)

    valid_u, u_msg = validate_username(username)
    if not valid_u:
        return False, u_msg, None

    valid_p, p_msg = validate_password(password)
    if not valid_p:
        return False, p_msg, None

    clean_user = username.strip()
    clean_role = "admin" if role.lower() == "admin" else "user"

    pw_hash = hash_password(password)
    conn = get_connection(db_path)
    try:
        with conn:
            cur = conn.execute(
                """
                INSERT INTO users (username, password_hash, role, is_active)
                VALUES (?, ?, ?, 1)
                """,
                (clean_user, pw_hash, clean_role),
            )
            return True, "Account registered successfully.", cur.lastrowid
    except sqlite3.IntegrityError:
        return False, f"Username '{clean_user}' is already registered. Please choose another username.", None
    finally:
        conn.close()


def authenticate_user(
    username: str,
    password: str,
    db_path: Optional[Path] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Authenticate a user.
    Validates existence, active status, and password hash.
    Updates last_login timestamp upon success.
    """
    init_auth_db(db_path)

    if not username or not password:
        return False, "Please enter both username and password.", None

    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            "SELECT id, username, password_hash, role, is_active FROM users WHERE username = ? COLLATE NOCASE;",
            (username.strip(),),
        )
        row = cur.fetchone()

        if not row:
            return False, "Invalid username or password.", None

        if row["is_active"] != 1:
            return False, "This account is currently deactivated. Please contact an administrator.", None

        if not verify_password(password, row["password_hash"]):
            return False, "Invalid username or password.", None

        # Update last login
        with conn:
            conn.execute(
                "UPDATE users SET last_login = datetime('now', 'localtime') WHERE id = ?;",
                (row["id"],),
            )

        user_info = {
            "id": row["id"],
            "username": row["username"],
            "role": row["role"],
            "is_active": bool(row["is_active"]),
        }
        return True, "Authentication successful.", user_info
    finally:
        conn.close()


def get_user_by_id(user_id: int, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Fetch user profile by user ID."""
    init_auth_db(db_path)
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            "SELECT id, username, role, is_active, created_at, last_login FROM users WHERE id = ?;",
            (int(user_id),),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_username(username: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Fetch user profile by username."""
    init_auth_db(db_path)
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            "SELECT id, username, role, is_active, created_at, last_login FROM users WHERE username = ? COLLATE NOCASE;",
            (username.strip(),),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_all_users(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Fetch all registered accounts for administrative inspection."""
    init_auth_db(db_path)
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            "SELECT id, username, role, is_active, created_at, last_login FROM users ORDER BY id ASC;"
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def update_user_status(
    target_user_id: int,
    new_is_active: bool,
    caller_role: str,
    caller_id: int,
    db_path: Optional[Path] = None,
) -> Tuple[bool, str]:
    """
    Enable or deactivate a user account.
    Enforces administrative authorization and prevents an admin from deactivating themselves.
    """
    init_auth_db(db_path)

    if caller_role != "admin":
        return False, "Access denied: Only administrators can modify account status."

    if target_user_id == caller_id and not new_is_active:
        return False, "Security restriction: You cannot deactivate your own administrative account."

    conn = get_connection(db_path)
    try:
        with conn:
            cur = conn.execute(
                "UPDATE users SET is_active = ? WHERE id = ?;",
                (1 if new_is_active else 0, int(target_user_id)),
            )
            if cur.rowcount == 0:
                return False, f"User ID #{target_user_id} not found."
            status_text = "activated" if new_is_active else "deactivated"
            return True, f"Account #{target_user_id} has been {status_text}."
    finally:
        conn.close()


def update_user_role(
    target_user_id: int,
    new_role: str,
    caller_role: str,
    caller_id: int,
    db_path: Optional[Path] = None,
) -> Tuple[bool, str]:
    """
    Update a user's role.
    Enforces administrative authorization and prevents demoting the last active administrator.
    """
    init_auth_db(db_path)

    if caller_role != "admin":
        return False, "Access denied: Only administrators can modify user roles."

    clean_role = new_role.lower().strip()
    if clean_role not in ["admin", "user"]:
        return False, "Invalid role. Role must be 'admin' or 'user'."

    conn = get_connection(db_path)
    try:
        with conn:
            # Check target user
            target = conn.execute("SELECT id, role FROM users WHERE id = ?;", (int(target_user_id),)).fetchone()
            if not target:
                return False, f"User ID #{target_user_id} not found."

            if target["role"] == "admin" and clean_role != "admin":
                # Ensure at least one other active admin remains
                admin_count = conn.execute(
                    "SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = 1 AND id != ?;",
                    (int(target_user_id),),
                ).fetchone()[0]
                if admin_count < 1:
                    return False, "Security restriction: Cannot demote the last remaining active administrator."

            conn.execute("UPDATE users SET role = ? WHERE id = ?;", (clean_role, int(target_user_id)))
            return True, f"Role for user #{target_user_id} updated to '{clean_role}'."
    finally:
        conn.close()


def provision_initial_admin(
    username: str,
    password: str,
    db_path: Optional[Path] = None,
) -> Tuple[bool, str]:
    """
    Provision the initial administrator account during setup.
    Allowed only if zero administrators exist in the database.
    """
    init_auth_db(db_path)
    existing_admins = count_admins(db_path)
    if existing_admins > 0:
        return False, "An administrator already exists. Further admin accounts must be created by an existing admin."

    success, msg, _ = register_user(username, password, role="admin", db_path=db_path)
    if success:
        return True, f"Initial administrator '{username.strip()}' provisioned successfully."
    return False, msg
