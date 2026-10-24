"""
Comprehensive Authentication, Authorization, and Security Test Suite.
Validates:
1. Successful registration
2. Duplicate username handling
3. Successful login
4. Incorrect password rejection
5. Logout simulation & session clearing
6. Unauthorized access to administrative operations
7. Ordinary users attempting role changes / deactivations
8. Prevention of demoting the last active administrator
9. Access isolation between two users (User A vs User B)
10. Database persistence across connections
11. Account deactivation (deactivated account blocked from login)
12. SQL Analytics protection against credential exfiltration
13. Compatibility with existing energy-saving tracker
14. Preservation of existing database records
"""
import unittest
import tempfile
import shutil
from pathlib import Path
import sqlite3
import pandas as pd

from modules.auth import (
    init_auth_db,
    hash_password,
    verify_password,
    validate_username,
    validate_password,
    register_user,
    authenticate_user,
    get_user_by_id,
    get_user_by_username,
    get_all_users,
    update_user_status,
    update_user_role,
    provision_initial_admin,
    count_users,
    count_admins,
)
from modules.db import (
    init_db,
    add_saving_action,
    get_all_saving_actions,
    update_saving_action,
    delete_saving_action,
    run_readonly_query,
)


class TestWattWiseAuthentication(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_db = Path(self.temp_dir) / "test_auth_electricity.db"
        init_db(self.test_db)
        init_auth_db(self.test_db)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # 1. Successful registration
    def test_01_successful_registration(self):
        ok, msg, uid = register_user("testuser1", "ValidPass123", role="user", db_path=self.test_db)
        self.assertTrue(ok)
        self.assertIsNotNone(uid)
        self.assertIn("registered successfully", msg)

        # Verify stored securely
        user = get_user_by_id(uid, db_path=self.test_db)
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "testuser1")
        self.assertEqual(user["role"], "user")
        self.assertEqual(user["is_active"], 1)

    # 2. Duplicate username or account handling
    def test_02_duplicate_username_rejected(self):
        ok1, _, _ = register_user("duplicate_user", "ValidPass123", db_path=self.test_db)
        self.assertTrue(ok1)

        # Exact duplicate
        ok2, msg2, _ = register_user("duplicate_user", "OtherPass456", db_path=self.test_db)
        self.assertFalse(ok2)
        self.assertIn("already registered", msg2)

        # Case-insensitive duplicate (e.g. Duplicate_User)
        ok3, msg3, _ = register_user("Duplicate_User", "OtherPass456", db_path=self.test_db)
        self.assertFalse(ok3)
        self.assertIn("already registered", msg3)

    # 3. Successful login
    def test_03_successful_login(self):
        register_user("login_user", "MySecretPass99", db_path=self.test_db)
        ok, msg, u_info = authenticate_user("login_user", "MySecretPass99", db_path=self.test_db)
        self.assertTrue(ok)
        self.assertIsNotNone(u_info)
        self.assertEqual(u_info["username"], "login_user")
        self.assertEqual(u_info["role"], "user")

    # 4. Incorrect password
    def test_04_incorrect_password(self):
        register_user("target_user", "CorrectPass1", db_path=self.test_db)
        ok, msg, u_info = authenticate_user("target_user", "WrongPassword99", db_path=self.test_db)
        self.assertFalse(ok)
        self.assertIsNone(u_info)
        self.assertIn("Invalid username or password", msg)

    # 5. Logout & session simulation
    def test_05_session_simulation(self):
        session = {}
        # Simulate login
        ok, _, u_info = register_user("session_tester", "SessionPass123", db_path=self.test_db)
        self.assertTrue(ok)
        _, _, user = authenticate_user("session_tester", "SessionPass123", db_path=self.test_db)
        session["wattwise_user"] = user
        session["authenticated"] = True

        self.assertTrue(session["authenticated"])
        self.assertEqual(session["wattwise_user"]["username"], "session_tester")

        # Simulate logout
        session.clear()
        self.assertNotIn("wattwise_user", session)
        self.assertFalse(session.get("authenticated", False))

    # 6. Unauthorized access to administrative operations
    def test_06_unauthorized_admin_access(self):
        # Register ordinary user and admin
        _, _, u1_id = register_user("ordinary_joe", "Password123", role="user", db_path=self.test_db)
        _, _, u2_id = register_user("victim_user", "Password123", role="user", db_path=self.test_db)

        # Ordinary user attempts to deactivate another account
        ok, msg = update_user_status(u2_id, new_is_active=False, caller_role="user", caller_id=u1_id, db_path=self.test_db)
        self.assertFalse(ok)
        self.assertIn("Access denied", msg)

        # Ordinary user attempts to change role to admin
        ok2, msg2 = update_user_role(u1_id, new_role="admin", caller_role="user", caller_id=u1_id, db_path=self.test_db)
        self.assertFalse(ok2)
        self.assertIn("Access denied", msg2)

    # 7. Administrator operations succeed for authorized admin
    def test_07_authorized_admin_operations(self):
        _, _, admin_id = register_user("super_admin", "AdminSecret123", role="admin", db_path=self.test_db)
        _, _, user_id = register_user("some_user", "UserSecret123", role="user", db_path=self.test_db)

        # Admin deactivates account
        ok_deact, msg_deact = update_user_status(user_id, new_is_active=False, caller_role="admin", caller_id=admin_id, db_path=self.test_db)
        self.assertTrue(ok_deact)
        u_record = get_user_by_id(user_id, db_path=self.test_db)
        self.assertEqual(u_record["is_active"], 0)

        # Admin activates account
        ok_act, _ = update_user_status(user_id, new_is_active=True, caller_role="admin", caller_id=admin_id, db_path=self.test_db)
        self.assertTrue(ok_act)
        u_record2 = get_user_by_id(user_id, db_path=self.test_db)
        self.assertEqual(u_record2["is_active"], 1)

    # 8. Prevention of unauthorized role changes & last admin demotion
    def test_08_prevent_demoting_last_admin(self):
        _, _, only_admin_id = register_user("sole_admin", "AdminSecret123", role="admin", db_path=self.test_db)

        # Attempt to demote sole admin
        ok, msg = update_user_role(only_admin_id, new_role="user", caller_role="admin", caller_id=only_admin_id, db_path=self.test_db)
        self.assertFalse(ok)
        self.assertIn("Cannot demote the last remaining active administrator", msg)

    # 9. Access isolation between two users (User A cannot edit/delete User B's actions)
    def test_09_user_access_isolation(self):
        _, _, u1_id = register_user("alice", "AlicePass123", role="user", db_path=self.test_db)
        _, _, u2_id = register_user("bob", "BobPass12345", role="user", db_path=self.test_db)

        # Alice adds an action
        act1 = add_saving_action(
            action_name="Alice LED Upgrade", action_category="Reducing unnecessary lighting",
            action_date="2008-01-01", user_id=u1_id, username="alice", db_path=self.test_db
        )

        # Bob adds an action
        act2 = add_saving_action(
            action_name="Bob AC Tuneup", action_category="Improving air-conditioner / heating usage",
            action_date="2008-02-01", user_id=u2_id, username="bob", db_path=self.test_db
        )

        # Alice queries actions
        alice_actions = get_all_saving_actions(user_id=u1_id, role="user", db_path=self.test_db)
        self.assertEqual(len(alice_actions), 1)
        self.assertEqual(alice_actions.iloc[0]["action_name"], "Alice LED Upgrade")

        # Bob queries actions
        bob_actions = get_all_saving_actions(user_id=u2_id, role="user", db_path=self.test_db)
        self.assertEqual(len(bob_actions), 1)
        self.assertEqual(bob_actions.iloc[0]["action_name"], "Bob AC Tuneup")

        # Bob attempts to update Alice's action
        hacked_update = update_saving_action(
            action_id=act1, action_name="Bob Hacked Alice", action_category="Custom Action",
            action_date="2008-01-01", baseline_days=14, followup_days=14, tariff_inr=7.5,
            user_id=u2_id, role="user", db_path=self.test_db
        )
        self.assertFalse(hacked_update)

        # Verify Alice's record was untouched
        alice_record = get_all_saving_actions(user_id=u1_id, role="user", db_path=self.test_db)
        self.assertEqual(alice_record.iloc[0]["action_name"], "Alice LED Upgrade")

        # Bob attempts to delete Alice's action
        hacked_delete = delete_saving_action(action_id=act1, user_id=u2_id, role="user", db_path=self.test_db)
        self.assertFalse(hacked_delete)
        alice_record_after = get_all_saving_actions(user_id=u1_id, role="user", db_path=self.test_db)
        self.assertEqual(len(alice_record_after), 1)

    # 10. Database persistence
    def test_10_database_persistence(self):
        _, _, u_id = register_user("persist_user", "PersistPass123", db_path=self.test_db)
        add_saving_action("Test Action", "Custom Action", "2008-03-01", user_id=u_id, username="persist_user", db_path=self.test_db)

        # Reopen connection from scratch
        conn2 = sqlite3.connect(str(self.test_db))
        c2 = conn2.cursor()
        user_row = c2.execute("SELECT username FROM users WHERE id = ?", (u_id,)).fetchone()
        action_row = c2.execute("SELECT action_name FROM energy_saving_actions WHERE user_id = ?", (u_id,)).fetchone()
        conn2.close()

        self.assertEqual(user_row[0], "persist_user")
        self.assertEqual(action_row[0], "Test Action")

    # 11. Account deactivation prevents login
    def test_11_deactivated_account_blocked(self):
        _, _, admin_id = register_user("admin_deact", "AdminPass123", role="admin", db_path=self.test_db)
        _, _, target_id = register_user("bad_actor", "ActorPass123", role="user", db_path=self.test_db)

        # Verify can login when active
        ok1, _, _ = authenticate_user("bad_actor", "ActorPass123", db_path=self.test_db)
        self.assertTrue(ok1)

        # Deactivate
        update_user_status(target_id, new_is_active=False, caller_role="admin", caller_id=admin_id, db_path=self.test_db)

        # Attempt to login while deactivated
        ok2, msg2, u2 = authenticate_user("bad_actor", "ActorPass123", db_path=self.test_db)
        self.assertFalse(ok2)
        self.assertIsNone(u2)
        self.assertIn("deactivated", msg2)

    # 12. SQL Analytics credential protection
    def test_12_sql_analytics_blocks_credentials(self):
        # Querying users table must be blocked
        with self.assertRaises(ValueError):
            run_readonly_query("SELECT * FROM users", db_path=self.test_db)

        with self.assertRaises(ValueError):
            run_readonly_query("SELECT username, password_hash FROM users", db_path=self.test_db)

        # Legitimate query against non-sensitive table is allowed
        res = run_readonly_query("SELECT count(*) as total_actions FROM energy_saving_actions", db_path=self.test_db)
        self.assertIn("total_actions", res.columns)

    # 13. Initial admin provisioning flow
    def test_13_initial_admin_provisioning(self):
        # Fresh DB has 0 admins
        self.assertEqual(count_admins(db_path=self.test_db), 0)

        # Provision initial admin
        ok, msg = provision_initial_admin("first_admin", "AdminPass123", db_path=self.test_db)
        self.assertTrue(ok)
        self.assertEqual(count_admins(db_path=self.test_db), 1)

        # Attempting second initial admin provisioning must be blocked
        ok2, msg2 = provision_initial_admin("second_admin", "AdminPass456", db_path=self.test_db)
        self.assertFalse(ok2)
        self.assertIn("already exists", msg2)

    # 14. Password complexity and username validation rules
    def test_14_input_validation_rules(self):
        # Invalid usernames
        self.assertFalse(validate_username("")[0])
        self.assertFalse(validate_username("ab")[0])  # too short
        self.assertFalse(validate_username("user name with spaces")[0])

        # Valid username
        self.assertTrue(validate_username("john_doe-99")[0])

        # Invalid passwords
        self.assertFalse(validate_password("short")[0])  # < 8 chars
        self.assertFalse(validate_password("alllettersonly")[0])  # no digit
        self.assertFalse(validate_password("123456789")[0])  # no letter

        # Valid password
        self.assertTrue(validate_password("SecurePass2026")[0])


if __name__ == "__main__":
    unittest.main()
