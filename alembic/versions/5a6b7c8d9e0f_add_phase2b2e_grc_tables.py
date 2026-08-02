"""add_phase2b2e_grc_tables

Adds the Phase 2b-2e GRC tables:
- Controls (control_categories, controls, control_tests, control_evidence)
- Risk Register (risk_items, risk_scenarios, risk_treatment_plans, risk_acceptances, risk_history)
- Compliance (compliance_frameworks, framework_requirements, control_mappings, compliance_gaps, compliance_assessments)
- Audit (audit_programs, audit_plans, audit_procedures, audit_findings, audit_evidence_collections, audit_interviews)
- Corrective Actions (corrective_actions, action_tasks, effectiveness_reviews)

Revision ID: 5a6b7c8d9e0f
Revises: 4f5e6d7c8b9a
Create Date: 2026-07-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5a6b7c8d9e0f'
down_revision: Union[str, Sequence[str], None] = '4f5e6d7c8b9a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to Phase 2b-2e GRC tables."""

    # ── Control Library ──────────────────────────────────────────────
    op.create_table(
        'control_categories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('control_type', sa.String(length=30), nullable=True),
        sa.Column('ics_control_domain', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_control_categories_name'),
    )

    op.create_table(
        'controls',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('control_category_id', sa.Integer(), nullable=True),
        sa.Column('control_id', sa.String(length=50), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('control_type', sa.String(length=30), nullable=True),
        sa.Column('implementation_status', sa.String(length=30), nullable=True),
        sa.Column('effectiveness_rating', sa.String(length=20), nullable=True),
        sa.Column('automation_level', sa.String(length=20), nullable=True),
        sa.Column('frequency', sa.String(length=50), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.Column('evidence_required', sa.Boolean(), nullable=False),
        sa.Column('evidence_description', sa.Text(), nullable=True),
        sa.Column('last_reviewed_date', sa.Date(), nullable=True),
        sa.Column('next_review_date', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['control_category_id'], ['control_categories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('control_id', name='uq_controls_control_id'),
    )
    op.create_index('ix_controls_control_category_id', 'controls', ['control_category_id'], unique=False)

    op.create_table(
        'control_tests',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('control_id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=True),
        sa.Column('tester_id', sa.Integer(), nullable=True),
        sa.Column('test_date', sa.Date(), nullable=True),
        sa.Column('test_method', sa.String(length=50), nullable=True),
        sa.Column('test_procedure', sa.Text(), nullable=True),
        sa.Column('result', sa.String(length=30), nullable=True),
        sa.Column('result_details', sa.Text(), nullable=True),
        sa.Column('evidence_path', sa.String(length=500), nullable=True),
        sa.Column('next_test_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['extended_assets.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['control_id'], ['controls.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tester_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_control_tests_control_id', 'control_tests', ['control_id'], unique=False)

    op.create_table(
        'control_evidence',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('control_id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=True),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_type', sa.String(length=50), nullable=True),
        sa.Column('evidence_type', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('collected_by_id', sa.Integer(), nullable=True),
        sa.Column('collected_date', sa.Date(), nullable=True),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.Column('is_current', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['extended_assets.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['collected_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['control_id'], ['controls.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_control_evidence_control_id', 'control_evidence', ['control_id'], unique=False)

    # ── Risk Register & Treatment ───────────────────────────────────
    op.create_table(
        'risk_items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('plant_id', sa.Integer(), nullable=True),
        sa.Column('asset_id', sa.Integer(), nullable=True),
        sa.Column('threat_id', sa.Integer(), nullable=True),
        sa.Column('vulnerability_id', sa.Integer(), nullable=True),
        sa.Column('bayesian_risk_result_id', sa.Integer(), nullable=True),
        sa.Column('risk_id', sa.String(length=50), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('scenario', sa.Text(), nullable=True),
        sa.Column('inherent_likelihood', sa.Float(), nullable=True),
        sa.Column('inherent_impact', sa.Float(), nullable=True),
        sa.Column('inherent_risk', sa.Float(), nullable=True),
        sa.Column('inherent_risk_level', sa.String(length=20), nullable=True),
        sa.Column('residual_likelihood', sa.Float(), nullable=True),
        sa.Column('residual_impact', sa.Float(), nullable=True),
        sa.Column('residual_risk', sa.Float(), nullable=True),
        sa.Column('residual_risk_level', sa.String(length=20), nullable=True),
        sa.Column('bayesian_likelihood', sa.Float(), nullable=True),
        sa.Column('bayesian_risk_score', sa.Float(), nullable=True),
        sa.Column('bayesian_risk_level', sa.String(length=20), nullable=True),
        sa.Column('risk_type', sa.String(length=50), nullable=True),
        sa.Column('risk_category', sa.String(length=100), nullable=True),
        sa.Column('root_cause', sa.Text(), nullable=True),
        sa.Column('consequence', sa.Text(), nullable=True),
        sa.Column('treatment_strategy', sa.String(length=30), nullable=True),
        sa.Column('treatment_status', sa.String(length=30), nullable=True),
        sa.Column('risk_owner_id', sa.Integer(), nullable=True),
        sa.Column('review_frequency', sa.String(length=30), nullable=True),
        sa.Column('last_reviewed_date', sa.Date(), nullable=True),
        sa.Column('next_review_date', sa.Date(), nullable=True),
        sa.Column('is_accepted', sa.Boolean(), nullable=False),
        sa.Column('accepted_by_id', sa.Integer(), nullable=True),
        sa.Column('acceptance_date', sa.Date(), nullable=True),
        sa.Column('acceptance_reason', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['accepted_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['asset_id'], ['extended_assets.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['bayesian_risk_result_id'], ['risk_results.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['plant_id'], ['plants.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['risk_owner_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['threat_id'], ['threats.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['vulnerability_id'], ['vulnerabilities.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('risk_id', name='uq_risk_items_risk_id'),
    )
    op.create_index('ix_risk_items_organization_id', 'risk_items', ['organization_id'], unique=False)
    op.create_index('ix_risk_items_plant_id', 'risk_items', ['plant_id'], unique=False)
    op.create_index('ix_risk_items_asset_id', 'risk_items', ['asset_id'], unique=False)
    op.create_index('ix_risk_items_status', 'risk_items', ['status'], unique=False)

    op.create_table(
        'risk_scenarios',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('risk_item_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('evidence_used', sa.JSON(), nullable=True),
        sa.Column('inherent_risk', sa.Float(), nullable=True),
        sa.Column('residual_risk', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['risk_item_id'], ['risk_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'risk_treatment_plans',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('risk_item_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('treatment_option', sa.String(length=30), nullable=True),
        sa.Column('target_date', sa.Date(), nullable=True),
        sa.Column('cost_estimate', sa.Float(), nullable=True),
        sa.Column('cost_currency', sa.String(length=3), nullable=True),
        sa.Column('responsible_person_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('approval_status', sa.String(length=30), nullable=False),
        sa.Column('approved_by_id', sa.Integer(), nullable=True),
        sa.Column('approval_date', sa.Date(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('effectiveness_review_required', sa.Boolean(), nullable=False),
        sa.Column('effectiveness_review_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['approved_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['responsible_person_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['risk_item_id'], ['risk_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'risk_acceptances',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('risk_item_id', sa.Integer(), nullable=False),
        sa.Column('accepted_by_id', sa.Integer(), nullable=False),
        sa.Column('acceptance_type', sa.String(length=30), nullable=True),
        sa.Column('justification', sa.Text(), nullable=False),
        sa.Column('expiration_date', sa.Date(), nullable=True),
        sa.Column('reviewing_authority', sa.String(length=255), nullable=True),
        sa.Column('conditions', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['accepted_by_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['risk_item_id'], ['risk_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'risk_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('risk_item_id', sa.Integer(), nullable=False),
        sa.Column('changed_by_id', sa.Integer(), nullable=True),
        sa.Column('change_type', sa.String(length=50), nullable=True),
        sa.Column('previous_values', sa.JSON(), nullable=True),
        sa.Column('new_values', sa.JSON(), nullable=True),
        sa.Column('change_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['changed_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['risk_item_id'], ['risk_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── Compliance Framework ────────────────────────────────────────
    op.create_table(
        'compliance_frameworks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('publisher', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('domain', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'version', name='uq_frameworks_name_version'),
    )

    op.create_table(
        'framework_requirements',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('framework_id', sa.Integer(), nullable=False),
        sa.Column('requirement_id', sa.String(length=50), nullable=False),
        sa.Column('parent_requirement_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('requirement_type', sa.String(length=50), nullable=True),
        sa.Column('implementation_guidance', sa.Text(), nullable=True),
        sa.Column('evidence_requirements', sa.Text(), nullable=True),
        sa.Column('weight_importance', sa.String(length=20), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['framework_id'], ['compliance_frameworks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_requirement_id'], ['framework_requirements.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('framework_id', 'requirement_id', name='uq_framework_requirement'),
    )
    op.create_index('ix_framework_requirements_framework_id', 'framework_requirements', ['framework_id'], unique=False)

    op.create_table(
        'control_mappings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('control_id', sa.Integer(), nullable=False),
        sa.Column('requirement_id', sa.Integer(), nullable=False),
        sa.Column('mapping_type', sa.String(length=30), nullable=True),
        sa.Column('mapping_notes', sa.Text(), nullable=True),
        sa.Column('mapping_justification', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['control_id'], ['controls.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requirement_id'], ['framework_requirements.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('control_id', 'requirement_id', name='uq_control_requirement_mapping'),
    )

    op.create_table(
        'compliance_gaps',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('plant_id', sa.Integer(), nullable=True),
        sa.Column('requirement_id', sa.Integer(), nullable=False),
        sa.Column('gap_description', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=True),
        sa.Column('remediation_plan', sa.Text(), nullable=True),
        sa.Column('target_closure_date', sa.Date(), nullable=True),
        sa.Column('closed_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['plant_id'], ['plants.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['requirement_id'], ['framework_requirements.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_compliance_gaps_requirement_id', 'compliance_gaps', ['requirement_id'], unique=False)

    op.create_table(
        'compliance_assessments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('plant_id', sa.Integer(), nullable=True),
        sa.Column('framework_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('assessment_date', sa.Date(), nullable=True),
        sa.Column('assessor_id', sa.Integer(), nullable=True),
        sa.Column('overall_status', sa.String(length=30), nullable=True),
        sa.Column('compliance_percentage', sa.Float(), nullable=True),
        sa.Column('findings_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['assessor_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['framework_id'], ['compliance_frameworks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['plant_id'], ['plants.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_compliance_assessments_framework_id', 'compliance_assessments', ['framework_id'], unique=False)

    # ── Audit Management ────────────────────────────────────────────
    op.create_table(
        'audit_programs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('program_type', sa.String(length=50), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('program_manager_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['program_manager_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'audit_plans',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('audit_program_id', sa.Integer(), nullable=True),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('plant_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('audit_type', sa.String(length=50), nullable=True),
        sa.Column('scope', sa.Text(), nullable=True),
        sa.Column('objectives', sa.Text(), nullable=True),
        sa.Column('criteria', sa.Text(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('estimated_hours', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('lead_auditor_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['audit_program_id'], ['audit_programs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lead_auditor_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['plant_id'], ['plants.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'audit_procedures',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('audit_plan_id', sa.Integer(), nullable=False),
        sa.Column('control_id', sa.Integer(), nullable=True),
        sa.Column('requirement_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('procedure_steps', sa.Text(), nullable=True),
        sa.Column('testing_method', sa.String(length=50), nullable=True),
        sa.Column('sample_size', sa.Integer(), nullable=True),
        sa.Column('expected_evidence', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['audit_plan_id'], ['audit_plans.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['control_id'], ['controls.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['requirement_id'], ['framework_requirements.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'audit_findings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('audit_plan_id', sa.Integer(), nullable=False),
        sa.Column('procedure_id', sa.Integer(), nullable=True),
        sa.Column('asset_id', sa.Integer(), nullable=True),
        sa.Column('control_id', sa.Integer(), nullable=True),
        sa.Column('finding_id', sa.String(length=50), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('finding_type', sa.String(length=50), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=True),
        sa.Column('likelihood', sa.String(length=20), nullable=True),
        sa.Column('criteria_reference', sa.String(length=255), nullable=True),
        sa.Column('root_cause', sa.Text(), nullable=True),
        sa.Column('impact', sa.Text(), nullable=True),
        sa.Column('recommendation', sa.Text(), nullable=True),
        sa.Column('management_response', sa.Text(), nullable=True),
        sa.Column('response_by_id', sa.Integer(), nullable=True),
        sa.Column('response_date', sa.Date(), nullable=True),
        sa.Column('acceptance_of_finding', sa.Boolean(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['extended_assets.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['audit_plan_id'], ['audit_plans.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['control_id'], ['controls.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['procedure_id'], ['audit_procedures.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['response_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('finding_id', name='uq_audit_findings_finding_id'),
    )
    op.create_index('ix_audit_findings_audit_plan_id', 'audit_findings', ['audit_plan_id'], unique=False)
    op.create_index('ix_audit_findings_severity', 'audit_findings', ['severity'], unique=False)

    op.create_table(
        'audit_evidence_collections',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('audit_plan_id', sa.Integer(), nullable=False),
        sa.Column('procedure_id', sa.Integer(), nullable=True),
        sa.Column('evidence_title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('filename', sa.String(length=255), nullable=True),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('evidence_type', sa.String(length=50), nullable=True),
        sa.Column('collected_by_id', sa.Integer(), nullable=True),
        sa.Column('collected_date', sa.DateTime(), nullable=False),
        sa.Column('is_confidential', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['audit_plan_id'], ['audit_plans.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['collected_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['procedure_id'], ['audit_procedures.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'audit_interviews',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('audit_plan_id', sa.Integer(), nullable=False),
        sa.Column('interviewee_name', sa.String(length=255), nullable=False),
        sa.Column('interviewee_title', sa.String(length=255), nullable=True),
        sa.Column('interviewee_department', sa.String(length=255), nullable=True),
        sa.Column('interviewer_id', sa.Integer(), nullable=True),
        sa.Column('interview_date', sa.DateTime(), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('topics_covered', sa.Text(), nullable=True),
        sa.Column('key_findings', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['audit_plan_id'], ['audit_plans.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['interviewer_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── Corrective Actions (CAPA) ───────────────────────────────────
    op.create_table(
        'corrective_actions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('finding_id', sa.Integer(), nullable=True),
        sa.Column('risk_item_id', sa.Integer(), nullable=True),
        sa.Column('compliance_gap_id', sa.Integer(), nullable=True),
        sa.Column('action_id', sa.String(length=50), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('root_cause_type', sa.String(length=50), nullable=True),
        sa.Column('root_cause_description', sa.Text(), nullable=True),
        sa.Column('impact_assessment', sa.Text(), nullable=True),
        sa.Column('action_type', sa.String(length=30), nullable=True),
        sa.Column('priority', sa.String(length=20), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('assigned_to_id', sa.Integer(), nullable=True),
        sa.Column('assigned_by_id', sa.Integer(), nullable=True),
        sa.Column('assigned_date', sa.Date(), nullable=True),
        sa.Column('target_date', sa.Date(), nullable=True),
        sa.Column('extended_date', sa.Date(), nullable=True),
        sa.Column('completed_date', sa.Date(), nullable=True),
        sa.Column('implementation_description', sa.Text(), nullable=True),
        sa.Column('implementation_evidence', sa.Text(), nullable=True),
        sa.Column('verifier_id', sa.Integer(), nullable=True),
        sa.Column('verification_date', sa.Date(), nullable=True),
        sa.Column('verification_result', sa.String(length=30), nullable=True),
        sa.Column('verification_notes', sa.Text(), nullable=True),
        sa.Column('closure_notes', sa.Text(), nullable=True),
        sa.Column('is_closed', sa.Boolean(), nullable=False),
        sa.Column('closed_by_id', sa.Integer(), nullable=True),
        sa.Column('closed_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['assigned_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['assigned_to_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['closed_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['compliance_gap_id'], ['compliance_gaps.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['finding_id'], ['audit_findings.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['risk_item_id'], ['risk_items.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['verifier_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('action_id', name='uq_corrective_actions_action_id'),
    )
    op.create_index('ix_corrective_actions_status', 'corrective_actions', ['status'], unique=False)
    op.create_index('ix_corrective_actions_assigned_to_id', 'corrective_actions', ['assigned_to_id'], unique=False)

    op.create_table(
        'action_tasks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('corrective_action_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('assigned_to_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('completed_date', sa.Date(), nullable=True),
        sa.Column('completion_notes', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['assigned_to_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['corrective_action_id'], ['corrective_actions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'effectiveness_reviews',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('corrective_action_id', sa.Integer(), nullable=False),
        sa.Column('review_date', sa.Date(), nullable=True),
        sa.Column('reviewer_id', sa.Integer(), nullable=True),
        sa.Column('criteria', sa.Text(), nullable=True),
        sa.Column('result', sa.String(length=30), nullable=True),
        sa.Column('findings', sa.Text(), nullable=True),
        sa.Column('follow_up_required', sa.Boolean(), nullable=False),
        sa.Column('follow_up_action', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['corrective_action_id'], ['corrective_actions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewer_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Downgrade schema: drop Phase 2b-2e GRC tables."""
    op.drop_table('effectiveness_reviews')
    op.drop_table('action_tasks')
    op.drop_index('ix_corrective_actions_assigned_to_id', table_name='corrective_actions')
    op.drop_index('ix_corrective_actions_status', table_name='corrective_actions')
    op.drop_table('corrective_actions')
    op.drop_table('audit_interviews')
    op.drop_table('audit_evidence_collections')
    op.drop_index('ix_audit_findings_severity', table_name='audit_findings')
    op.drop_index('ix_audit_findings_audit_plan_id', table_name='audit_findings')
    op.drop_table('audit_findings')
    op.drop_table('audit_procedures')
    op.drop_table('audit_plans')
    op.drop_table('audit_programs')
    op.drop_index('ix_compliance_assessments_framework_id', table_name='compliance_assessments')
    op.drop_table('compliance_assessments')
    op.drop_index('ix_compliance_gaps_requirement_id', table_name='compliance_gaps')
    op.drop_table('compliance_gaps')
    op.drop_table('control_mappings')
    op.drop_index('ix_framework_requirements_framework_id', table_name='framework_requirements')
    op.drop_table('framework_requirements')
    op.drop_table('compliance_frameworks')
    op.drop_table('risk_history')
    op.drop_table('risk_acceptances')
    op.drop_table('risk_treatment_plans')
    op.drop_table('risk_scenarios')
    op.drop_index('ix_risk_items_status', table_name='risk_items')
    op.drop_index('ix_risk_items_asset_id', table_name='risk_items')
    op.drop_index('ix_risk_items_plant_id', table_name='risk_items')
    op.drop_index('ix_risk_items_organization_id', table_name='risk_items')
    op.drop_table('risk_items')
    op.drop_index('ix_control_evidence_control_id', table_name='control_evidence')
    op.drop_table('control_evidence')
    op.drop_index('ix_control_tests_control_id', table_name='control_tests')
    op.drop_table('control_tests')
    op.drop_index('ix_controls_control_category_id', table_name='controls')
    op.drop_table('controls')
    op.drop_table('control_categories')

