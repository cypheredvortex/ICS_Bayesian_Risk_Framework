"""add_phase1_grc_tables

Adds the Phase 1 GRC foundation tables:
- Organization hierarchy (organizations, sites, plants, departments)
- User & Access Control (roles, users, user_sessions)
- Zones & Conduits (security_zones, conduits)
- Extended Asset Register (asset_categories, extended_assets, asset_dependencies)
- Audit Trail (audit_logs)

Revision ID: 2a8b9c0d1e2f
Revises: 3f1fade8e943
Create Date: 2026-07-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2a8b9c0d1e2f'
down_revision: Union[str, Sequence[str], None] = '3f1fade8e943'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to Phase 1 GRC tables."""
    # ── Organization hierarchy ────────────────────────────────────────────
    op.create_table(
        'organizations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('legal_name', sa.String(length=255), nullable=True),
        sa.Column('registration_number', sa.String(length=100), nullable=True),
        sa.Column('tax_id', sa.String(length=100), nullable=True),
        sa.Column('industry_sector', sa.String(length=100), nullable=True),
        sa.Column('address_line1', sa.String(length=255), nullable=True),
        sa.Column('address_line2', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('postal_code', sa.String(length=20), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('website', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_organizations_name'),
    )
    op.create_index('ix_organizations_name', 'organizations', ['name'], unique=False)

    op.create_table(
        'sites',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=True),
        sa.Column('site_type', sa.String(length=50), nullable=True),
        sa.Column('address_line1', sa.String(length=255), nullable=True),
        sa.Column('address_line2', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('postal_code', sa.String(length=20), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('timezone', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'name', name='uq_sites_org_name'),
    )
    op.create_index('ix_sites_organization_id', 'sites', ['organization_id'], unique=False)

    op.create_table(
        'plants',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('site_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=True),
        sa.Column('plant_type', sa.String(length=100), nullable=True),
        sa.Column('ics_domain', sa.String(length=100), nullable=True),
        sa.Column('criticality_level', sa.String(length=20), nullable=True),
        sa.Column('operational_status', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('site_id', 'name', name='uq_plants_site_name'),
    )
    op.create_index('ix_plants_site_id', 'plants', ['site_id'], unique=False)

    op.create_table(
        'departments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('plant_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=True),
        sa.Column('manager_name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['plant_id'], ['plants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── User & Access Control ────────────────────────────────────────────
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_system_role', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('role_id', sa.Integer(), nullable=True),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('job_title', sa.String(length=255), nullable=True),
        sa.Column('department_name', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_locked', sa.Boolean(), nullable=False),
        sa.Column('password_changed_at', sa.DateTime(), nullable=True),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email'),
    )
    op.create_index('ix_users_organization_id', 'users', ['organization_id'], unique=False)
    op.create_index('ix_users_role_id', 'users', ['role_id'], unique=False)

    op.create_table(
        'user_sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=500), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_sessions_user_id', 'user_sessions', ['user_id'], unique=False)
    op.create_index('ix_user_sessions_token', 'user_sessions', ['token'], unique=False)

    # ── Zones & Conduits (IEC 62443) ─────────────────────────────────────
    op.create_table(
        'security_zones',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('plant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('zone_level', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color_hex', sa.String(length=7), nullable=True),
        sa.Column('classification', sa.String(length=50), nullable=True),
        sa.Column('access_requirements', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['plant_id'], ['plants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('plant_id', 'name', name='uq_security_zones_plant_name'),
    )
    op.create_index('ix_security_zones_plant_id', 'security_zones', ['plant_id'], unique=False)

    op.create_table(
        'conduits',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('plant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('source_zone_id', sa.Integer(), nullable=False),
        sa.Column('destination_zone_id', sa.Integer(), nullable=False),
        sa.Column('conduit_type', sa.String(length=50), nullable=True),
        sa.Column('communication_protocols', sa.Text(), nullable=True),
        sa.Column('security_requirements', sa.Text(), nullable=True),
        sa.Column('is_encrypted', sa.Boolean(), nullable=False),
        sa.Column('is_physically_secured', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['plant_id'], ['plants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_zone_id'], ['security_zones.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['destination_zone_id'], ['security_zones.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('plant_id', 'name', name='uq_conduits_plant_name'),
    )
    op.create_index('ix_conduits_plant_id', 'conduits', ['plant_id'], unique=False)

    # ── Extended Asset Register ──────────────────────────────────────────
    op.create_table(
        'asset_categories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('ics_category', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['parent_id'], ['asset_categories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    op.create_table(
        'extended_assets',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('site_id', sa.Integer(), nullable=True),
        sa.Column('plant_id', sa.Integer(), nullable=True),
        sa.Column('security_zone_id', sa.Integer(), nullable=True),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('asset_tag', sa.String(length=100), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('alias', sa.String(length=255), nullable=True),
        sa.Column('serial_number', sa.String(length=100), nullable=True),
        sa.Column('asset_type', sa.String(length=100), nullable=True),
        sa.Column('sub_type', sa.String(length=100), nullable=True),
        sa.Column('criticality', sa.String(length=20), nullable=True),
        sa.Column('data_sensitivity', sa.String(length=50), nullable=True),
        sa.Column('vendor', sa.String(length=255), nullable=True),
        sa.Column('model', sa.String(length=255), nullable=True),
        sa.Column('firmware_version', sa.String(length=100), nullable=True),
        sa.Column('software_version', sa.String(length=100), nullable=True),
        sa.Column('operating_system', sa.String(length=100), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('mac_address', sa.String(length=17), nullable=True),
        sa.Column('network_segment', sa.String(length=255), nullable=True),
        sa.Column('operational_status', sa.String(length=50), nullable=True),
        sa.Column('commissioning_date', sa.Date(), nullable=True),
        sa.Column('last_maintenance_date', sa.Date(), nullable=True),
        sa.Column('expected_lifetime_years', sa.Integer(), nullable=True),
        sa.Column('exposure_level', sa.String(length=20), nullable=True),
        sa.Column('patch_level', sa.String(length=20), nullable=True),
        sa.Column('availability_requirement', sa.String(length=20), nullable=True),
        sa.Column('integrity_requirement', sa.String(length=20), nullable=True),
        sa.Column('confidentiality_requirement', sa.String(length=20), nullable=True),
        sa.Column('intrinsic_probability', sa.Float(), nullable=True),
        sa.Column('consequence_severity', sa.Float(), nullable=True),
        sa.Column('asset_owner_id', sa.Integer(), nullable=True),
        sa.Column('technical_owner_id', sa.Integer(), nullable=True),
        sa.Column('location_building', sa.String(length=255), nullable=True),
        sa.Column('location_room', sa.String(length=255), nullable=True),
        sa.Column('location_rack', sa.String(length=100), nullable=True),
        sa.Column('location_rack_position', sa.Integer(), nullable=True),
        sa.Column('x_position', sa.Float(), nullable=True),
        sa.Column('y_position', sa.Float(), nullable=True),
        sa.Column('lifecycle_status', sa.String(length=30), nullable=True),
        sa.Column('decommissioned_date', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['asset_owner_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['technical_owner_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['category_id'], ['asset_categories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['plant_id'], ['plants.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['security_zone_id'], ['security_zones.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_extended_assets_organization_id', 'extended_assets', ['organization_id'], unique=False)
    op.create_index('ix_extended_assets_site_id', 'extended_assets', ['site_id'], unique=False)
    op.create_index('ix_extended_assets_plant_id', 'extended_assets', ['plant_id'], unique=False)
    op.create_index('ix_extended_assets_zone_id', 'extended_assets', ['security_zone_id'], unique=False)
    op.create_index('ix_extended_assets_name', 'extended_assets', ['name'], unique=False)

    op.create_table(
        'asset_dependencies',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('depends_on_asset_id', sa.Integer(), nullable=False),
        sa.Column('dependency_type', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('criticality', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['extended_assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['depends_on_asset_id'], ['extended_assets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('asset_id', 'depends_on_asset_id', 'dependency_type', name='uq_asset_dependency'),
    )

    # ── Audit Trail ──────────────────────────────────────────────────────
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('entity_type', sa.String(length=100), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('changes', sa.JSON(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_logs_entity', 'audit_logs', ['entity_type', 'entity_id'], unique=False)
    op.create_index('ix_audit_logs_user', 'audit_logs', ['user_id'], unique=False)
    op.create_index('ix_audit_logs_created', 'audit_logs', ['created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema: drop Phase 1 GRC tables."""
    op.drop_index('ix_audit_logs_created', table_name='audit_logs')
    op.drop_index('ix_audit_logs_user', table_name='audit_logs')
    op.drop_index('ix_audit_logs_entity', table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_table('asset_dependencies')
    op.drop_index('ix_extended_assets_name', table_name='extended_assets')
    op.drop_index('ix_extended_assets_zone_id', table_name='extended_assets')
    op.drop_index('ix_extended_assets_plant_id', table_name='extended_assets')
    op.drop_index('ix_extended_assets_site_id', table_name='extended_assets')
    op.drop_index('ix_extended_assets_organization_id', table_name='extended_assets')
    op.drop_table('extended_assets')
    op.drop_table('asset_categories')
    op.drop_index('ix_conduits_plant_id', table_name='conduits')
    op.drop_table('conduits')
    op.drop_index('ix_security_zones_plant_id', table_name='security_zones')
    op.drop_table('security_zones')
    op.drop_index('ix_user_sessions_token', table_name='user_sessions')
    op.drop_index('ix_user_sessions_user_id', table_name='user_sessions')
    op.drop_table('user_sessions')
    op.drop_index('ix_users_role_id', table_name='users')
    op.drop_index('ix_users_organization_id', table_name='users')
    op.drop_table('users')
    op.drop_table('roles')
    op.drop_table('departments')
    op.drop_index('ix_plants_site_id', table_name='plants')
    op.drop_table('plants')
    op.drop_index('ix_sites_organization_id', table_name='sites')
    op.drop_table('sites')
    op.drop_index('ix_organizations_name', table_name='organizations')
    op.drop_table('organizations')

