"""API router for Authentication and User Management.

Uses bcrypt password hashing and JWT access tokens via ``backend.security``.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.database.config import get_session_factory
from backend.database.repositories import (
    AuditLogRepository,
    RoleRepository,
    UserRepository,
    UserSessionRepository,
)
from backend.routers.common import get_db
from backend.schemas import (
    LoginRequest,
    LoginResponse,
    PasswordChangeRequest,
    RoleCreate,
    RoleResponse,
    UserCreate,
    UserMeResponse,
    UserResponse,
    UserUpdate,
)
from backend.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    DISABLE_AUTH,
    create_access_token,
    create_session_token,
    get_current_user,
    get_role_permissions,
    hash_password,
    migrate_legacy_hash,
    require_admin,
    verify_password,
)
from backend.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

# Imported by other routers for route protection.
__all__ = ["get_current_user", "require_permission", "require_module_access", "require_admin", "router"]


# ═══════════════════════════════════════════════════════════════
# Role Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/roles", response_model=list[RoleResponse], tags=["Roles"])
def list_roles(
    db: Session = Depends(get_db),
    _: None = Depends(get_current_user),
):
    """List all roles."""
    return RoleRepository(db).list_all()


@router.post("/roles", response_model=RoleResponse, status_code=201, tags=["Roles"])
def create_role(
    payload: RoleCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    """Create a new role. Requires admin permission."""
    repo = RoleRepository(db)
    existing = repo.get_by_name(payload.name)
    if existing:
        raise HTTPException(status_code=409, detail=f"Role '{payload.name}' already exists.")
    role = repo.create(**payload.model_dump(exclude_unset=True))
    return role


# ═══════════════════════════════════════════════════════════════
# User Endpoints
# ═══════════════════════════════════════════════════════════════


@router.post("/users", response_model=UserResponse, status_code=201, tags=["Users"])
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    """Create a new user. Requires admin permission."""
    repo = UserRepository(db)
    existing_username = repo.get_by_username(payload.username)
    if existing_username:
        raise HTTPException(status_code=409, detail="Username already taken.")
    existing_email = repo.get_by_email(payload.email)
    if existing_email:
        raise HTTPException(status_code=409, detail="Email already registered.")

    user_data = payload.model_dump(exclude={"password"})
    user_data["password_hash"] = hash_password(payload.password)
    user = repo.create(**user_data)
    return user


@router.get("/users", response_model=list[UserResponse], tags=["Users"])
def list_users(
    organization_id: int | None = None,
    db: Session = Depends(get_db),
    _: None = Depends(get_current_user),
):
    """List all users, optionally filtered by organization."""
    repo = UserRepository(db)
    if organization_id:
        return repo.list_for_organization(organization_id)
    return repo.list_all()


@router.get("/users/{user_id}", response_model=UserResponse, tags=["Users"])
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(get_current_user),
):
    """Get user details."""
    repo = UserRepository(db)
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@router.put("/users/{user_id}", response_model=UserResponse, tags=["Users"])
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    """Update a user. Requires admin permission."""
    repo = UserRepository(db)
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    update_data = payload.model_dump(exclude_unset=True, exclude_none=True)
    for key, value in update_data.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


@router.post("/users/me/change-password", tags=["Users"])
def change_own_password(
    payload: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Change the current user's password (self-service)."""
    repo = UserRepository(db)
    user = repo.get_by_id(current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    # Verify current password
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    user.password_hash = hash_password(payload.new_password)
    user.password_changed_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Password updated successfully."}


@router.post("/users/{user_id}/change-password", tags=["Users"])
def change_password(
    user_id: int,
    payload: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Change a user's password (admin only)."""
    require_admin(current_user)
    repo = UserRepository(db)
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.password_hash = hash_password(payload.new_password)
    user.password_changed_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Password updated successfully."}


# ═══════════════════════════════════════════════════════════════
# Authentication Endpoints
# ═══════════════════════════════════════════════════════════════


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Authenticate user and return a JWT access token."""
    user_repo = UserRepository(db)
    session_repo = UserSessionRepository(db)

    # Find user by username or email
    user = user_repo.get_by_username(payload.username)
    if not user:
        user = user_repo.get_by_email(payload.username)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is disabled.")

    if user.is_locked:
        raise HTTPException(status_code=401, detail="Account is locked.")

    # Verify password: try bcrypt first, then migrate legacy PBKDF2 hash.
    password_ok = verify_password(payload.password, user.password_hash)
    if not password_ok and _is_legacy_hash(user.password_hash):
        password_ok = migrate_legacy_hash(payload.password, user.password_hash)
        if password_ok:
            # Upgrade to bcrypt on successful legacy login.
            user.password_hash = hash_password(payload.password)
            user.password_changed_at = datetime.now(timezone.utc)
            db.commit()

    if not password_ok:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    # Create JWT access token
    access_token = create_access_token(user)

    # Also record an opaque session for audit/invalidation support.
    session_token = create_session_token()
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    session_repo.create_session(
        user_id=user.id,
        token=session_token,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    # Audit log login event
    try:
        AuditLogRepository(db).log(
            user_id=user.id,
            action="login",
            entity_type="user",
            entity_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except Exception:
        logger.exception("Failed to write audit log for login")

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    """Invalidate the current session token."""
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip()
    if token:
        session_repo = UserSessionRepository(db)
        session = session_repo.get_active_by_token(token)
        if session:
            session.is_active = False
            db.commit()
    return {"message": "Logged out successfully."}


@router.get("/me", response_model=UserMeResponse)
def me(current_user=Depends(get_current_user)):
    """Return the current authenticated user's profile with role name and permissions."""
    role_name = current_user.role.name if current_user.role else None
    permissions = sorted(get_role_permissions(role_name)) if role_name else []
    # Build UserMeResponse from the User ORM model plus role/permission extras.
    return UserMeResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        job_title=current_user.job_title,
        organization_id=current_user.organization_id,
        role_id=current_user.role_id,
        department_name=current_user.department_name,
        is_active=current_user.is_active,
        is_locked=current_user.is_locked,
        last_login_at=current_user.last_login_at,
        created_at=current_user.created_at,
        role_name=role_name,
        permissions=permissions,
    )


def _is_legacy_hash(stored_hash: str) -> bool:
    """Detect the legacy 'salt_hex:key_hex' PBKDF2 format."""
    if not stored_hash or ":" not in stored_hash:
        return False
    try:
        salt_hex, key_hex = stored_hash.split(":")
        bytes.fromhex(salt_hex)
        bytes.fromhex(key_hex)
        return True
    except (ValueError, AttributeError):
        return False

