"""
Database management and SQLite operations for WattWise.
Safely connects to electricity.db and manages tables without altering raw datasets.
Provides user-isolated persistence and protection against unauthorized credential access.
"""
from pathlib import Path
import sqlite3
import re
from typing import Any, Dict, List, Optional
import pandas as pd

DB_PATH = Path("electricity.db")


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Return a connection to the SQLite database with row factory enabled."""
    target = db_path or DB_PATH
    conn = sqlite3.connect(str(target))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    """Ensure required application and authentication tables exist in the database."""
    conn = get_connection(db_path)
    try:
        with conn:
            # 1. Base energy_saving_actions table
            conn.execute("""
            CREATE TABLE IF NOT EXISTS energy_saving_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_name TEXT NOT NULL,
                action_category TEXT NOT NULL,
                action_date TEXT NOT NULL,
                baseline_days INTEGER NOT NULL DEFAULT 14,
                followup_days INTEGER NOT NULL DEFAULT 14,
                tariff_inr REAL NOT NULL DEFAULT 7.50,
                notes TEXT,
                user_id INTEGER,
                username TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );
            """)

            # Non-destructive column check for legacy tables
            cursor = conn.execute("PRAGMA table_info(energy_saving_actions);")
            existing_cols = {row["name"] for row in cursor.fetchall()}
            if "user_id" not in existing_cols:
                conn.execute("ALTER TABLE energy_saving_actions ADD COLUMN user_id INTEGER;")
            if "username" not in existing_cols:
                conn.execute("ALTER TABLE energy_saving_actions ADD COLUMN username TEXT;")

            # 2. Authentication users table
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
    finally:
        conn.close()


def add_saving_action(
    action_name: str,
    action_category: str,
    action_date: str,
    baseline_days: int = 14,
    followup_days: int = 14,
    tariff_inr: float = 7.50,
    notes: str = "",
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> int:
    """Insert a new energy-saving action associated with an authenticated user account."""
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO energy_saving_actions (
                    action_name, action_category, action_date,
                    baseline_days, followup_days, tariff_inr, notes,
                    user_id, username
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    action_name.strip(),
                    action_category.strip(),
                    str(action_date),
                    int(baseline_days),
                    int(followup_days),
                    float(tariff_inr),
                    notes.strip() if notes else "",
                    user_id,
                    username.strip() if username else None,
                ),
            )
            return cursor.lastrowid
    finally:
        conn.close()


def get_all_saving_actions(
    user_id: Optional[Any] = None,
    role: str = "admin",
    db_path: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Fetch energy-saving actions as a pandas DataFrame.
    If role == 'admin' or user_id is None, returns all actions.
    If role == 'user', enforces user isolation returning only actions belonging to that user.
    """
    if isinstance(user_id, (Path, str)):
        db_path = Path(user_id)
        user_id = None
        role = "admin"

    init_db(db_path)
    conn = get_connection(db_path)
    try:
        if role == "admin" or user_id is None:
            query = "SELECT * FROM energy_saving_actions ORDER BY action_date DESC, id DESC;"
            return pd.read_sql_query(query, conn)
        else:
            query = """
            SELECT * FROM energy_saving_actions
            WHERE user_id = ?
            ORDER BY action_date DESC, id DESC;
            """
            return pd.read_sql_query(query, conn, params=(int(user_id),))
    finally:
        conn.close()


def update_saving_action(
    action_id: int,
    action_name: str,
    action_category: str,
    action_date: str,
    baseline_days: int,
    followup_days: int,
    tariff_inr: float,
    notes: str = "",
    user_id: Optional[Any] = None,
    role: str = "admin",
    db_path: Optional[Path] = None,
) -> bool:
    """
    Update an existing energy-saving action record.
    Enforces user ownership check on server-side to prevent parameter tampering.
    """
    if isinstance(user_id, (Path, str)):
        db_path = Path(user_id)
        user_id = None
        role = "admin"

    init_db(db_path)
    conn = get_connection(db_path)
    try:
        with conn:
            if role == "admin" or user_id is None:
                cursor = conn.execute(
                    """
                    UPDATE energy_saving_actions
                    SET action_name = ?,
                        action_category = ?,
                        action_date = ?,
                        baseline_days = ?,
                        followup_days = ?,
                        tariff_inr = ?,
                        notes = ?
                    WHERE id = ?
                    """,
                    (
                        action_name.strip(),
                        action_category.strip(),
                        str(action_date),
                        int(baseline_days),
                        int(followup_days),
                        float(tariff_inr),
                        notes.strip() if notes else "",
                        int(action_id),
                    ),
                )
            else:
                cursor = conn.execute(
                    """
                    UPDATE energy_saving_actions
                    SET action_name = ?,
                        action_category = ?,
                        action_date = ?,
                        baseline_days = ?,
                        followup_days = ?,
                        tariff_inr = ?,
                        notes = ?
                    WHERE id = ? AND user_id = ?
                    """,
                    (
                        action_name.strip(),
                        action_category.strip(),
                        str(action_date),
                        int(baseline_days),
                        int(followup_days),
                        float(tariff_inr),
                        notes.strip() if notes else "",
                        int(action_id),
                        int(user_id),
                    ),
                )
            return cursor.rowcount > 0
    finally:
        conn.close()


def delete_saving_action(
    action_id: int,
    user_id: Optional[Any] = None,
    role: str = "admin",
    db_path: Optional[Path] = None,
) -> bool:
    """
    Delete an energy-saving action by ID.
    Enforces server-side ownership verification.
    """
    if isinstance(user_id, (Path, str)):
        db_path = Path(user_id)
        user_id = None
        role = "admin"

    init_db(db_path)
    conn = get_connection(db_path)
    try:
        with conn:
            if role == "admin" or user_id is None:
                cursor = conn.execute(
                    "DELETE FROM energy_saving_actions WHERE id = ?;",
                    (int(action_id),),
                )
            else:
                cursor = conn.execute(
                    "DELETE FROM energy_saving_actions WHERE id = ? AND user_id = ?;",
                    (int(action_id), int(user_id)),
                )
            return cursor.rowcount > 0
    finally:
        conn.close()


def run_readonly_query(
    sql_query: str,
    db_path: Optional[Path] = None,
    limit: int = 500,
) -> pd.DataFrame:
    """
    Safely execute a read-only SQL query against the SQLite database.
    Rejects any statement attempting data modification.
    Blocks queries attempting to read the users table or extract credentials.
    """
    cleaned = sql_query.strip().strip(";").strip()
    first_token = cleaned.split()[0].upper() if cleaned.split() else ""
    disallowed = {"INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "REPLACE", "ATTACH", "DETACH"}
    if first_token in disallowed:
        raise ValueError(f"Disallowed SQL statement: {first_token}. Only SELECT queries are permitted.")

    # Security rule: Protect credentials and user accounts from SQL Analytics
    upper_query = cleaned.upper()
    if re.search(r"\bUSERS\b", upper_query) or "PASSWORD_HASH" in upper_query:
        raise ValueError("Access denied: The 'users' authentication table contains protected credentials and cannot be accessed via SQL Analytics.")

    conn = get_connection(db_path)
    try:
        if "LIMIT" not in upper_query:
            wrapped_query = f"SELECT * FROM ({cleaned}) LIMIT {limit}"
        else:
            wrapped_query = cleaned
        return pd.read_sql_query(wrapped_query, conn)
    finally:
        conn.close()
