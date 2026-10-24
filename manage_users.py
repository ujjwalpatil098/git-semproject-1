"""
WattWise User & Admin Management CLI Tool.
Allows offline server-side provisioning and administration without storing hardcoded credentials.
Usage:
  python manage_users.py create-admin --username <user> --password <pass>
  python manage_users.py create-user --username <user> --password <pass>
  python manage_users.py list-users
  python manage_users.py set-status (--username <user> | --id <id>) --active <1|0>
  python manage_users.py set-role (--username <user> | --id <id>) --role <admin|user>
  python manage_users.py reset-password (--username <user> | --id <id>) --password <pass>
"""
import sys
import argparse
from pathlib import Path
from modules.auth import (
    init_auth_db,
    register_user,
    get_all_users,
    get_user_by_id,
    get_user_by_username,
    update_user_status,
    update_user_role,
    hash_password,
    get_connection,
)


def resolve_user(args, db_path=None):
    if getattr(args, "id", None) is not None:
        return get_user_by_id(args.id, db_path=db_path)
    elif getattr(args, "username", None) is not None:
        return get_user_by_username(args.username, db_path=db_path)
    return None


def main():
    parser = argparse.ArgumentParser(description="WattWise User Management Utility")
    parser.add_argument("--db-path", default=None, help="Path to SQLite database (default: electricity.db)")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # create-admin
    p_admin = subparsers.add_parser("create-admin", help="Create a new administrator account")
    p_admin.add_argument("--username", required=True, help="Admin username")
    p_admin.add_argument("--password", required=True, help="Admin password")

    # create-user
    p_user = subparsers.add_parser("create-user", help="Create a standard user account")
    p_user.add_argument("--username", required=True, help="Username")
    p_user.add_argument("--password", required=True, help="Password")

    # list-users
    subparsers.add_parser("list-users", help="List all registered user accounts")

    # set-status
    p_stat = subparsers.add_parser("set-status", help="Activate or deactivate a user account")
    g_stat = p_stat.add_mutually_exclusive_group(required=True)
    g_stat.add_argument("--username", help="Target username")
    g_stat.add_argument("--id", type=int, help="Target user ID")
    p_stat.add_argument("--active", type=int, choices=[0, 1], required=True, help="1 for active, 0 for inactive")

    # set-role
    p_role = subparsers.add_parser("set-role", help="Update a user's role")
    g_role = p_role.add_mutually_exclusive_group(required=True)
    g_role.add_argument("--username", help="Target username")
    g_role.add_argument("--id", type=int, help="Target user ID")
    p_role.add_argument("--role", choices=["admin", "user"], required=True, help="Role (admin or user)")

    # reset-password
    p_pw = subparsers.add_parser("reset-password", help="Reset a user's password")
    g_pw = p_pw.add_mutually_exclusive_group(required=True)
    g_pw.add_argument("--username", help="Target username")
    g_pw.add_argument("--id", type=int, help="Target user ID")
    p_pw.add_argument("--password", required=True, help="New password")

    args = parser.parse_args()

    db_path = Path(args.db_path) if args.db_path else None
    init_auth_db(db_path)

    if args.command == "create-admin":
        success, msg, uid = register_user(args.username, args.password, role="admin", db_path=db_path)
        print(f"[{'SUCCESS' if success else 'ERROR'}] {msg} (ID: {uid})")
        sys.exit(0 if success else 1)

    elif args.command == "create-user":
        success, msg, uid = register_user(args.username, args.password, role="user", db_path=db_path)
        print(f"[{'SUCCESS' if success else 'ERROR'}] {msg} (ID: {uid})")
        sys.exit(0 if success else 1)

    elif args.command == "list-users":
        users = get_all_users(db_path=db_path)
        print(f"\nTotal Registered Users: {len(users)}\n" + "-" * 75)
        print(f"{'ID':<5} {'Username':<20} {'Role':<10} {'Active':<8} {'Created':<20} {'Last Login'}")
        print("-" * 75)
        for u in users:
            print(f"{u['id']:<5} {u['username']:<20} {u['role']:<10} {str(bool(u['is_active'])):<8} {str(u['created_at'])[:19]:<20} {str(u['last_login'] or 'Never')}")
        print("-" * 75 + "\n")

    elif args.command == "set-status":
        user = resolve_user(args, db_path=db_path)
        if not user:
            print(f"[ERROR] User not found.")
            sys.exit(1)
        success, msg = update_user_status(user["id"], bool(args.active), caller_role="admin", caller_id=-1, db_path=db_path)
        print(f"[{'SUCCESS' if success else 'ERROR'}] {msg}")
        sys.exit(0 if success else 1)

    elif args.command == "set-role":
        user = resolve_user(args, db_path=db_path)
        if not user:
            print(f"[ERROR] User not found.")
            sys.exit(1)
        success, msg = update_user_role(user["id"], args.role, caller_role="admin", caller_id=-1, db_path=db_path)
        print(f"[{'SUCCESS' if success else 'ERROR'}] {msg}")
        sys.exit(0 if success else 1)

    elif args.command == "reset-password":
        user = resolve_user(args, db_path=db_path)
        if not user:
            print(f"[ERROR] User not found.")
            sys.exit(1)
        if len(args.password) < 8:
            print("[ERROR] Password must be at least 8 characters long.")
            sys.exit(1)
        pw_hash = hash_password(args.password)
        conn = get_connection(db_path)
        try:
            with conn:
                conn.execute("UPDATE users SET password_hash = ? WHERE id = ?;", (pw_hash, user["id"]))
            print(f"[SUCCESS] Password for user '{user['username']}' reset successfully.")
        finally:
            conn.close()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
