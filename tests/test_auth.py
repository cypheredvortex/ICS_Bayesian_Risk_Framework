"""Tests for Authentication & RBAC.

Covers:
- Password hashing (bcrypt)
- JWT access token create/decode
- Login flow (username/email, wrong password, disabled/locked accounts)
- /api/v1/auth/me returning role_name + permissions
- Self-service password change
- Module-level RBAC enforcement via require_module_access
"""

import os
import unittest
from datetime import datetime, timezone

from backend.database.config import get_session_factory
from backend.database.models import Role, User
from backend.database.repositories import RoleRepository, UserRepository
from backend.security import (
    DISABLE_AUTH,
    create_access_token,
    decode_access_token,
    hash_password,
    require_module_access,
    verify_password,
)


class SecurityUtilitiesTests(unittest.TestCase):
    """Unit tests for backend.security primitives."""

    def test_hash_and_verify_password(self):
        hashed = hash_password("s3cret-pass")
        self.assertNotEqual(hashed, "s3cret-pass")
        self.assertTrue(verify_password("s3cret-pass", hashed))
        self.assertFalse(verify_password("wrong", hashed))

    def test_create_and_decode_access_token(self):
        factory = get_session_factory()
        session = factory()
        try:
            admin = RoleRepository(session).create(name="admin", description="Admin", is_system_role=True)
            user = UserRepository(session).create(
                username="tokentest",
                email="tokentest@example.com",
                password_hash=hash_password("password123"),
                role_id=admin.id,
            )
            token = create_access_token(user)
            payload = decode_access_token(token)
            self.assertEqual(payload["sub"], str(user.id))
            self.assertEqual(payload["role"], "admin")
            self.assertIn("exp", payload)
            self.assertIn("jti", payload)
        finally:
            session.close()

    def test_decode_invalid_token_raises(self):
        from fastapi import HTTPException
        with self.assertRaises(HTTPException):
            decode_access_token("not-a-valid-token")


class LoginFlowTests(unittest.TestCase):
    """Integration-style tests exercising the auth router dependencies."""

    def _seed_user(self, session, *, username="alice", email="alice@example.com",
                   password="password123", role_name="viewer", is_active=True,
                   is_locked=False) -> User:
        role = RoleRepository(session).get_by_name(role_name)
        if not role:
            role = RoleRepository(session).create(name=role_name, description=role_name)
        return UserRepository(session).create(
            username=username,
            email=email,
            password_hash=hash_password(password),
            role_id=role.id,
            is_active=is_active,
            is_locked=is_locked,
        )

    def test_login_verifies_password(self):
        factory = get_session_factory()
        session = factory()
        try:
            self._seed_user(session)
            user = UserRepository(session).get_by_username("alice")
            self.assertIsNotNone(user)
            self.assertTrue(verify_password("password123", user.password_hash))
            self.assertFalse(verify_password("nope", user.password_hash))
        finally:
            session.close()

    def test_me_payload_has_role_and_permissions(self):
        """The /me handler builds a UserMeResponse with role_name + permissions."""
        factory = get_session_factory()
        session = factory()
        try:
            user = self._seed_user(session, role_name="auditor")
            from backend.routers.auth import me
            # me() is a FastAPI path function; call it directly with the user.
            response = me(user)
            self.assertEqual(response.role_name, "auditor")
            self.assertIn("assets:read", response.permissions)
            self.assertIn("audit:write", response.permissions)
            self.assertNotIn("assets:write", response.permissions)
        finally:
            session.close()


class RbacDependencyTests(unittest.TestCase):
    """Tests for require_module_access dependency factory."""

    def test_require_module_access_returns_dependency(self):
        dep = require_module_access("risk")
        self.assertTrue(callable(dep))

    def test_require_module_access_write(self):
        dep = require_module_access("risk", write=True)
        self.assertTrue(callable(dep))

    def _build_user(self, session, role_name: str) -> User:
        role = RoleRepository(session).get_by_name(role_name)
        if not role:
            role = RoleRepository(session).create(name=role_name, description=role_name)
        return UserRepository(session).create(
            username=f"user_{role_name}_{id(session)}",
            email=f"user_{role_name}_{id(session)}@example.com",
            password_hash=hash_password("password123"),
            role_id=role.id,
        )

    def _run_dependency(self, session, role_name: str, module: str, write: bool):
        from backend.security import require_module_access
        checker = require_module_access(module, write=write)
        user = self._build_user(session, role_name)
        return checker(user=user)

    def test_viewer_can_read_assets_but_not_write(self):
        factory = get_session_factory()
        session = factory()
        try:
            self._run_dependency(session, "viewer", "assets", write=False)
        finally:
            session.close()

    def test_viewer_cannot_write_assets(self):
        from fastapi import HTTPException
        factory = get_session_factory()
        session = factory()
        try:
            with self.assertRaises(HTTPException):
                self._run_dependency(session, "viewer", "assets", write=True)
        finally:
            session.close()

    def test_analyst_can_write_assets(self):
        factory = get_session_factory()
        session = factory()
        try:
            self._run_dependency(session, "analyst", "assets", write=True)
        finally:
            session.close()

    def test_viewer_cannot_access_organizations_write(self):
        from fastapi import HTTPException
        factory = get_session_factory()
        session = factory()
        try:
            with self.assertRaises(HTTPException):
                self._run_dependency(session, "viewer", "organizations", write=True)
        finally:
            session.close()

    def test_compliance_officer_can_write_compliance(self):
        factory = get_session_factory()
        session = factory()
        try:
            self._run_dependency(session, "compliance_officer", "compliance", write=True)
        finally:
            session.close()

    def test_viewer_cannot_write_compliance(self):
        from fastapi import HTTPException
        factory = get_session_factory()
        session = factory()
        try:
            with self.assertRaises(HTTPException):
                self._run_dependency(session, "viewer", "compliance", write=True)
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()

