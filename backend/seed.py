"""
Seed script to create initial admin user and demo data.

Usage:
    python -m backend.seed
    python -m backend.seed --demo  # Create demo users for all roles
"""
import argparse
import logging
import os
import sys

# Make sure we can import from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.config import initialize_database, get_session_factory
from backend.database.models import Role, User
from backend.security import hash_password

logger = logging.getLogger(__name__)


def seed_users(demo: bool = False):
    """Create default admin user and optionally demo users for all roles."""
    initialize_database()
    factory = get_session_factory()
    db = factory()

    try:
        # Check if admin user already exists
        existing = db.query(User).filter(User.username == "admin").first()
        if existing:
            print("Admin user already exists. Skipping seed.")
            return

        # Get the admin role
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            print("ERROR: Admin role not found. Run migrations first.")
            return

        # Create admin user
        admin = User(
            username="admin",
            email="admin@icsrisk.local",
            password_hash=hash_password("admin123"),
            first_name="System",
            last_name="Administrator",
            job_title="ICS Risk Administrator",
            is_active=True,
            is_locked=False,
            role_id=admin_role.id,
        )
        db.add(admin)
        print(f"Created admin user: admin / admin123")

        if demo:
            # Create demo users for each role
            demo_users = [
                ("auditor", "auditor", "auditor1", "Security Auditor", "Auditor"),
                ("risk_manager", "riskmanager", "risk123", "Risk", "Manager"),
                ("compliance_officer", "compliance", "comp123", "Compliance", "Officer"),
                ("analyst", "analyst", "analyst1", "Security", "Analyst"),
                ("viewer", "viewer", "viewer1", "Read-Only", "Viewer"),
            ]
            for role_name, username, password, first, last in demo_users:
                role = db.query(Role).filter(Role.name == role_name).first()
                if role:
                    user = User(
                        username=username,
                        email=f"{username}@icsrisk.local",
                        password_hash=hash_password(password),
                        first_name=first,
                        last_name=last,
                        job_title=f"{role_name.replace('_', ' ').title()}",
                        is_active=True,
                        is_locked=False,
                        role_id=role.id,
                    )
                    db.add(user)
                    print(f"Created {role_name} user: {username} / {password}")

        db.commit()
        print("\nSeed complete!")

    except Exception as e:
        db.rollback()
        logger.exception("Seed failed")
        print(f"ERROR: {e}")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Seed database with initial users")
    parser.add_argument("--demo", action="store_true", help="Create demo users for all roles")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    seed_users(demo=args.demo)


if __name__ == "__main__":
    main()
