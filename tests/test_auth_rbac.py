"""
Auth & RBAC integration tests.

Covers:
- Login flow (JWT issuance, expires_in, token_type)
- /auth/me returning role_name + permissions
- Self-service password change
- Module-level RBAC on GRC routers (read vs write permissions)

These tests use FastAPI's TestClient with the shared ``temp_db`` fixture
from conftest.py (a fresh temporary SQLite DB per test). The default roles
are seeded by ``initialize_database``.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

# Force auth ON so the dependency checks actually run.
os.environ["DISABLE_AUTH"] = "0"

from backend.api import app
from backend.database.config import get_session_factory
from backend.database.repositories import RoleRepository, UserRepository
from backend.security import hash_password

pytestmark = pytest.mark.usefixtures("temp_db")


def _make_user(username: str, role_name: str = "admin", password: str = "testpass123"):
    """Create a user directly in the DB (bypasses the API) for testing."""
    factory = get_session_factory()
    db = factory()
    try:
        role = RoleRepository(db).get_by_name(role_name)
        user = UserRepository(db).create(
            username=username,
            email=f"{username}@example.com",
            password_hash=hash_password(password),
            role_id=role.id if role else None,
            is_active=True,
            is_locked=False,
        )
        return user.id
    finally:
        db.close()


def _login(client: TestClient, username: str, password: str = "testpass123"):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.fixture()
def admin_token() -> str:
    """Fixture returning a valid JWT for an admin user."""
    _make_user("rbac_admin", "admin")
    client = TestClient(app)
    data = _login(client, "rbac_admin")
    return data["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ═══════════════════════════════════════════════════════════════
# Auth flow
# ═══════════════════════════════════════════════════════════════


def test_login_returns_token_and_expiry():
    """Login response must include access_token, token_type, and expires_in."""
    _make_user("login_user", "admin")
    client = TestClient(app)
    data = _login(client, "login_user")
    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert isinstance(data["expires_in"], int)
    assert data["expires_in"] > 0
    assert data["user"]["username"] == "login_user"


def test_login_wrong_password():
    """Wrong credentials must return 401."""
    _make_user("badpass_user", "admin")
    client = TestClient(app)
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "badpass_user", "password": "wrongpass"},
    )
    assert resp.status_code == 401


def test_me_returns_role_and_permissions():
    """/auth/me must resolve role_name and sorted permissions."""
    _make_user("me_user", "viewer")
    client = TestClient(app)
    token = _login(client, "me_user")["access_token"]
    resp = client.get("/api/v1/auth/me", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "me_user"
    assert body["role_name"] == "viewer"
    assert "assets:read" in body["permissions"]
    assert "risk:read" in body["permissions"]


def test_me_requires_auth():
    """/auth/me without a token must be rejected."""
    client = TestClient(app)
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_self_service_change_password():
    """A user can change their own password via /users/me/change-password."""
    _make_user("selfpwd_user", "admin")
    client = TestClient(app)
    token = _login(client, "selfpwd_user")["access_token"]

    resp = client.post(
        "/api/v1/auth/users/me/change-password",
        headers=_auth(token),
        json={"current_password": "testpass123", "new_password": "newpass456"},
    )
    assert resp.status_code == 200, resp.text

    # Old password should no longer work; new password should.
    bad = client.post(
        "/api/v1/auth/login",
        json={"username": "selfpwd_user", "password": "testpass123"},
    )
    assert bad.status_code == 401
    good = client.post(
        "/api/v1/auth/login",
        json={"username": "selfpwd_user", "password": "newpass456"},
    )
    assert good.status_code == 200


def test_self_service_change_password_requires_current():
    """Changing password without the correct current password must fail."""
    _make_user("selfpwd2_user", "admin")
    client = TestClient(app)
    token = _login(client, "selfpwd2_user")["access_token"]

    resp = client.post(
        "/api/v1/auth/users/me/change-password",
        headers=_auth(token),
        json={"current_password": "nope", "new_password": "newpass456"},
    )
    assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════
# RBAC: read endpoints
# ═══════════════════════════════════════════════════════════════


def test_viewer_can_read_assets():
    """A viewer has assets:read so GET /assets must succeed."""
    _make_user("viewer_rbac", "viewer")
    client = TestClient(app)
    token = _login(client, "viewer_rbac")["access_token"]
    resp = client.get("/api/v1/assets/", headers=_auth(token))
    assert resp.status_code == 200


def test_viewer_cannot_write_assets():
    """A viewer lacks assets:write so POST /assets must be forbidden."""
    _make_user("viewer_rbac2", "viewer")
    client = TestClient(app)
    token = _login(client, "viewer_rbac2")["access_token"]
    resp = client.post(
        "/api/v1/assets/",
        headers=_auth(token),
        json={"name": "Unauthorized PLC"},
    )
    assert resp.status_code == 403


def test_analyst_can_write_vulnerabilities():
    """Analyst has vulnerabilities:write so POST /vulnerabilities must succeed."""
    _make_user("analyst_rbac", "analyst")
    client = TestClient(app)
    token = _login(client, "analyst_rbac")["access_token"]
    resp = client.post(
        "/api/v1/vulnerabilities/",
        headers=_auth(token),
        json={"name": "CVE Test", "cve_id": "CVE-2024-9999"},
    )
    assert resp.status_code == 201


def test_viewer_cannot_write_vulnerabilities():
    """Viewer lacks vulnerabilities:write so POST must be forbidden."""
    _make_user("viewer_vuln", "viewer")
    client = TestClient(app)
    token = _login(client, "viewer_vuln")["access_token"]
    resp = client.post(
        "/api/v1/vulnerabilities/",
        headers=_auth(token),
        json={"name": "Nope", "cve_id": "CVE-2024-9998"},
    )
    assert resp.status_code == 403


def test_auditor_can_read_audit_programs():
    """Auditor has audit:read so GET /audit/programs must succeed."""
    _make_user("auditor_rbac", "auditor")
    client = TestClient(app)
    token = _login(client, "auditor_rbac")["access_token"]
    resp = client.get("/api/v1/audit/programs", headers=_auth(token))
    assert resp.status_code == 200


def test_viewer_cannot_write_audit_plans():
    """Viewer lacks audit:write so POST /audit/plans must be forbidden."""
    _make_user("viewer_audit", "viewer")
    client = TestClient(app)
    token = _login(client, "viewer_audit")["access_token"]
    resp = client.post(
        "/api/v1/audit/plans",
        headers=_auth(token),
        json={"title": "Unauthorized plan"},
    )
    assert resp.status_code == 403


def test_risk_manager_can_create_risk_item():
    """Risk manager has risk:write so POST /risk/items must succeed."""
    _make_user("riskmanager_rbac", "risk_manager")
    client = TestClient(app)
    token = _login(client, "riskmanager_rbac")["access_token"]
    resp = client.post(
        "/api/v1/risk/items",
        headers=_auth(token),
        json={"title": "Test risk item"},
    )
    assert resp.status_code == 201


def test_viewer_cannot_create_risk_item():
    """Viewer lacks risk:write so POST /risk/items must be forbidden."""
    _make_user("viewer_risk", "viewer")
    client = TestClient(app)
    token = _login(client, "viewer_risk")["access_token"]
    resp = client.post(
        "/api/v1/risk/items",
        headers=_auth(token),
        json={"title": "Unauthorized risk"},
    )
    assert resp.status_code == 403


def test_compliance_officer_can_create_framework():
    """Compliance officer has compliance:write so POST /compliance/frameworks succeeds."""
    _make_user("compliance_rbac", "compliance_officer")
    client = TestClient(app)
    token = _login(client, "compliance_rbac")["access_token"]
    resp = client.post(
        "/api/v1/compliance/frameworks",
        headers=_auth(token),
        json={"name": "IEC 62443", "version": "2024"},
    )
    assert resp.status_code == 201


def test_viewer_cannot_create_framework():
    """Viewer lacks compliance:write so POST must be forbidden."""
    _make_user("viewer_comp", "viewer")
    client = TestClient(app)
    token = _login(client, "viewer_comp")["access_token"]
    resp = client.post(
        "/api/v1/compliance/frameworks",
        headers=_auth(token),
        json={"name": "Nope", "version": "1.0"},
    )
    assert resp.status_code == 403


def test_admin_can_do_everything():
    """Admin has '*' permission, so a mutating call must succeed."""
    _make_user("admin_rbac", "admin")
    client = TestClient(app)
    token = _login(client, "admin_rbac")["access_token"]
    resp = client.post(
        "/api/v1/organizations/",
        headers=_auth(token),
        json={"name": "Admin Org"},
    )
    assert resp.status_code == 201


def test_unauthenticated_request_forbidden():
    """Without a token, module endpoints must return 401."""
    client = TestClient(app)
    resp = client.get("/api/v1/assets/")
    assert resp.status_code == 401

