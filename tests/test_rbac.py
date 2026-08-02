"""Tests verifying RBAC wiring across all GRC routers.

The intent is that every endpoint in every GRC router carries a
``require_module_access`` dependency so that users lacking the module
permission are denied (403) while authorized users pass through.
"""

import unittest
from pathlib import Path
from unittest.mock import patch

from backend.routers import (
    assets,
    audit_management,
    capa,
    compliance,
    controls,
    organizations,
    risk,
    threats,
    vulnerabilities,
    zones,
)

# (router module, expected module name)
ROUTERS = [
    (compliance, "compliance"),
    (capa, "capa"),
    (controls, "controls"),
    (risk, "risk"),
    (audit_management, "audit"),
    (assets, "assets"),
    (threats, "threats"),
    (vulnerabilities, "vulnerabilities"),
    (zones, "zones"),
    (organizations, "organizations"),
]


class RbacWiringTests(unittest.TestCase):
    """Assert that each router module defines endpoints protected by RBAC."""

    def test_all_routers_import_require_module_access(self):
        """Each router must have imported the dependency factory."""
        for module, _ in ROUTERS:
            source = Path(module.__file__).read_text(encoding="utf-8")
            self.assertIn(
                "require_module_access",
                source,
                f"{module.__name__} does not use require_module_access",
            )

    def test_write_endpoints_use_write_permission(self):
        """Every POST/PUT/DELETE handler must carry a write=True dependency.

        The number of write-protected dependency references must be at least
        the number of mutating decorators in the module (a router may have
        more write deps than mutating handlers, never fewer).
        """
        for module, module_name in ROUTERS:
            source = Path(module.__file__).read_text(encoding="utf-8")
            mutating_count = (
                source.count("@router.post")
                + source.count("@router.put")
                + source.count("@router.delete")
            )
            write_refs = source.count(
                f'require_module_access("{module_name}", write=True)'
            )
            self.assertGreaterEqual(
                write_refs,
                mutating_count,
                f"{module.__name__}: {write_refs} write deps < {mutating_count} mutating handlers",
            )

    def test_read_endpoints_use_read_permission(self):
        """GET handlers must reference the module read permission.

        The number of read-module dependency references must be at least the
        number of GET decorators in the module.
        """
        for module, module_name in ROUTERS:
            source = Path(module.__file__).read_text(encoding="utf-8")
            get_count = source.count("@router.get")
            read_refs = source.count(
                f'require_module_access("{module_name}")'
            )
            self.assertGreaterEqual(
                read_refs,
                get_count,
                f"{module.__name__}: {read_refs} read deps < {get_count} GET handlers",
            )

    def test_require_module_access_called_in_every_endpoint(self):
        """Every path-decorated function body references require_module_access."""
        for module, module_name in ROUTERS:
            source = Path(module.__file__).read_text(encoding="utf-8")
            # Count decorators with route definitions
            route_count = source.count("@router.get") + source.count("@router.post") \
                + source.count("@router.put") + source.count("@router.delete")
            # Every endpoint must include a module access dependency line
            self.assertGreaterEqual(
                route_count,
                1,
                f"{module.__name__} has no routes",
            )
            total_refs = source.count(
                f'require_module_access("{module_name}")'
            ) + source.count(
                f'require_module_access("{module_name}", write=True)'
            )
            self.assertGreaterEqual(
                total_refs,
                route_count,
                f"{module.__name__}: {total_refs} RBAC deps < {route_count} routes",
            )

    def test_dependency_factory_returns_callable_that_enforces(self):
        """Behavioral check: a viewer user is rejected for write access."""
        from fastapi import HTTPException

        factory = require_dep = None  # imported below to avoid clobbering
        from backend.security import require_module_access
        checker = require_module_access("assets", write=True)

        from backend.database.config import get_session_factory
        from backend.database.models import Role, User
        from backend.database.repositories import RoleRepository, UserRepository
        from backend.security import hash_password

        session = get_session_factory()()
        try:
            role = RoleRepository(session).get_by_name("viewer")
            if not role:
                role = RoleRepository(session).create(name="viewer", description="viewer")
            user = UserRepository(session).create(
                username="rbac_viewer",
                email="rbac_viewer@example.com",
                password_hash=hash_password("password123"),
                role_id=role.id,
            )
            with self.assertRaises(HTTPException):
                checker(user=user)
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()

