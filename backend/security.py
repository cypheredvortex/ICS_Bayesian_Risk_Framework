"""
Security utilities for the ICS Risk Assessment Framework.

Provides production-grade authentication and authorization primitives:
- bcrypt password hashing (replaces PBKDF2-SHA256)
- JWT access token creation/verification
- FastAPI dependencies for route protection and role-based access control
- Optional authentication (falls back to unauthenticated when DISABLE_AUTH=1)
"""

from __future__ import annotations

import logging
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.database.config import get_session_factory
from backend.database.models import Role, User, UserSession

logger = logging.getLogger(__name__)

# ---- Configuration (env-driven) ----
SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-secret-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
# DISABLE_AUTH=1 allows unauthenticated access (useful for local/dev/demo
# mode and for the existing test suite). Production must set DISABLE_AUTH=0.
DISABLE_AUTH = os.getenv("DISABLE_AUTH", "0") in ("1", "true", "True", "yes")

_bearer_scheme = HTTPBearer(auto_error=False)

# Permissions catalog: role → set of permission codes. A permission code is
# "{module}:{action}" e.g. "risk:write", "audit:read".
# The viewer role has read-only access. admin has everything.
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {
        "*",
    },
    "auditor": {
        "assets:read", "threats:read", "vulnerabilities:read", "controls:read",
        "risk:read", "compliance:read", "audit:read", "audit:write",
        "capa:read", "capa:write", "organizations:read", "zones:read",
    },
    "risk_manager": {
        "assets:read", "threats:read", "vulnerabilities:read", "controls:read",
        "risk:read", "risk:write", "compliance:read", "audit:read",
        "capa:read", "capa:write", "organizations:read", "zones:read",
    },
    "compliance_officer": {
        "assets:read", "threats:read", "vulnerabilities:read", "controls:read",
        "controls:write", "risk:read", "compliance:read", "compliance:write",
        "audit:read", "capa:read", "organizations:read", "zones:read",
    },
    "analyst": {
        "assets:read", "assets:write", "threats:read", "vulnerabilities:read",
        "vulnerabilities:write", "controls:read", "risk:read", "compliance:read",
        "audit:read", "capa:read", "organizations:read",
        "zones:read", "zones:write",
    },
    "viewer": {
        "assets:read", "threats:read", "vulnerabilities:read", "controls:read",
        "risk:read", "compliance:read", "audit:read", "capa:read",
        "organizations:read", "zones:read",
    },
}

# Module → read/write permission mapping used by require_permission.
MODULE_ACTIONS: dict[str, tuple[str, str]] = {
    "assets": ("assets:read", "assets:write"),
    "threats": ("threats:read", "threats:write"),
    "vulnerabilities": ("vulnerabilities:read", "vulnerabilities:write"),
    "controls": ("controls:read", "controls:write"),
    "risk": ("risk:read", "risk:write"),
    "compliance": ("compliance:read", "compliance:write"),
    "audit": ("audit:read", "audit:write"),
    "capa": ("capa:read", "capa:write"),
    "organizations": ("organizations:read", "organizations:write"),
    "zones": ("zones:read", "zones:write"),
}


# ═══════════════════════════════════════════════════════════════
# Password Hashing (bcrypt)
# ═══════════════════════════════════════════════════════════════


def hash_password(password: str) -> str:
    """Hash a password using bcrypt with a per-password salt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
    except (ValueError, AttributeError):
        return False


def migrate_legacy_hash(password: str, stored_hash: str) -> bool:
    """Verify against a legacy PBKDF2-SHA256 hash (salt:hash hex format)."""
    try:
        salt_hex, key_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        stored_key = bytes.fromhex(key_hex)
        new_key = __import__("hashlib").pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, 100000
        )
        return new_key == stored_key
    except (ValueError, AttributeError):
        return False


# ═══════════════════════════════════════════════════════════════
# JWT Tokens
# ═══════════════════════════════════════════════════════════════


def create_access_token(user: User) -> str:
    """Create a JWT access token for a user."""
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user.id),
        "username": user.username,
        "email": user.email,
        "role": user.role.name if user.role else "viewer",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token. Raises HTTPException on failure."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ═══════════════════════════════════════════════════════════════
# Session token helpers (opaque token used by /auth/login)
# ═══════════════════════════════════════════════════════════════


def create_session_token() -> str:
    """Generate a cryptographically-secure opaque session token."""
    return secrets.token_urlsafe(48)


# ═══════════════════════════════════════════════════════════════
# FastAPI Dependencies
# ═══════════════════════════════════════════════════════════════


def _get_db():
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(_get_db),
) -> User:
    """Resolve the current user from the Authorization header (JWT).

    When DISABLE_AUTH=1, returns the first admin user (or None-tolerant)
    so local/demo/test mode continues to work unauthenticated.
    """
    if DISABLE_AUTH:
        return _get_demo_user(db)

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Provide a Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    user_id = int(payload.get("sub", 0))
    from backend.database.repositories import UserRepository

    user = UserRepository(db).get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists.")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is disabled.")
    if user.is_locked:
        raise HTTPException(status_code=401, detail="Account is locked.")
    return user


def _get_demo_user(db: Session) -> User:
    """Return the first active user for demo mode, or None (never raise)."""
    from backend.database.repositories import UserRepository

    users = UserRepository(db).list_all()
    for user in users:
        if user.is_active and not user.is_locked:
            return user
    # No user exists; create a synthetic one for read-only demo flow.
    user = User(
        username="demo",
        email="demo@example.com",
        password_hash="",
        role=db.query(Role).filter(Role.name == "admin").first(),
    )
    return user


def get_current_user_or_none(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(_get_db),
) -> User | None:
    """Resolve current user but never raise (used on public endpoints)."""
    if DISABLE_AUTH:
        return _get_demo_user(db)
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        from backend.database.repositories import UserRepository

        return UserRepository(db).get_by_id(int(payload.get("sub", 0)))
    except HTTPException:
        return None


def require_permission(permission: str):
    """Dependency factory: require a specific permission code, e.g. 'risk:write'."""

    def _checker(user: User = Depends(get_current_user)) -> User:
        if DISABLE_AUTH:
            return user
        if not user or not user.role:
            raise HTTPException(status_code=403, detail="No role assigned.")
        perms = ROLE_PERMISSIONS.get(user.role.name, set())
        if "*" in perms or permission in perms:
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing required permission: {permission}",
        )

    return _checker


def require_module_access(module: str, write: bool = False):
    """Dependency factory: require read or write access to a module.

    Example: ``require_module_access("risk", write=True)``.
    """
    read_perm, write_perm = MODULE_ACTIONS.get(module, (f"{module}:read", f"{module}:write"))
    permission = write_perm if write else read_perm
    return require_permission(permission)


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency: require platform administrator access (admin role)."""
    if DISABLE_AUTH:
        return user
    if not user or not user.role:
        raise HTTPException(status_code=403, detail="No role assigned.")
    perms = ROLE_PERMISSIONS.get(user.role.name, set())
    if "*" in perms or user.role.name == "admin":
        return user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Administrator privileges required.",
    )


def get_role_permissions(role_name: str) -> set[str]:
    """Return the permission set for a role name."""
    return ROLE_PERMISSIONS.get(role_name, set())

