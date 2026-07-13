"""Module 2 - Citizen Profile & Mock DigiLocker Integration

Revision ID: 002_citizen_profile_digilocker
Revises: 001_initial_schema
Create Date: 2024-01-02 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '002_citizen_profile_digilocker'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── citizen_profiles ──────────────────────────────────────────────────────
    op.create_table(
        'citizen_profiles',
        sa.Column('id', sa.CHAR(36), nullable=False),
        sa.Column('citizen_id', sa.CHAR(36), nullable=False),
        sa.Column('father_name', sa.String(100), nullable=True),
        sa.Column('mother_name', sa.String(100), nullable=True),
        sa.Column('occupation', sa.String(100), nullable=True),
        sa.Column('marital_status',
                  sa.Enum('single', 'married', 'widowed', 'divorced', 'separated'),
                  nullable=True),
        sa.Column('blood_group', sa.String(5), nullable=True),
        sa.Column('nationality', sa.String(50), nullable=True, server_default='Indian'),
        sa.Column('annual_income', sa.Float(), nullable=True),
        sa.Column('income_category',
                  sa.Enum('bpl', 'apl', 'ews', 'lig', 'mig', 'hig'),
                  nullable=True),
        sa.Column('caste', sa.String(100), nullable=True),
        sa.Column('community', sa.String(100), nullable=True),
        sa.Column('sub_caste', sa.String(100), nullable=True),
        sa.Column('religion', sa.String(50), nullable=True),
        sa.Column('is_disabled', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('disability_type', sa.String(100), nullable=True),
        sa.Column('disability_percentage', sa.Integer(), nullable=True),
        sa.Column('is_farmer', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('farmer_id', sa.String(50), nullable=True),
        sa.Column('education_level', sa.String(100), nullable=True),
        sa.Column('education_institution', sa.String(200), nullable=True),
        sa.Column('family_member_count', sa.Integer(), nullable=True),
        sa.Column('family_details', sa.Text(), nullable=True),
        sa.Column('profile_completion_percentage', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sync_status',
                  sa.Enum('not_synced', 'synced', 'sync_failed', 'sync_pending'),
                  nullable=False, server_default='not_synced'),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('citizen_id', name='uq_citizen_profiles_citizen_id'),
        sa.ForeignKeyConstraint(['citizen_id'], ['citizens.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_citizen_profile_citizen_id', 'citizen_profiles', ['citizen_id'])
    op.create_index('ix_citizen_profile_sync_status', 'citizen_profiles', ['sync_status'])
    op.create_index('ix_citizen_profile_income_category', 'citizen_profiles', ['income_category'])
    op.create_index('ix_citizen_profile_caste', 'citizen_profiles', ['caste'])
    op.create_index('ix_citizen_profile_is_farmer', 'citizen_profiles', ['is_farmer'])
    op.create_index('ix_citizen_profile_is_disabled', 'citizen_profiles', ['is_disabled'])

    # ── land_records ──────────────────────────────────────────────────────────
    op.create_table(
        'land_records',
        sa.Column('id', sa.CHAR(36), nullable=False),
        sa.Column('citizen_id', sa.CHAR(36), nullable=False),
        sa.Column('survey_number', sa.String(50), nullable=True),
        sa.Column('land_area', sa.Float(), nullable=True),
        sa.Column('land_area_unit', sa.String(20), nullable=True, server_default='acres'),
        sa.Column('land_type',
                  sa.Enum('agricultural', 'residential', 'commercial', 'forest', 'wasteland'),
                  nullable=True),
        sa.Column('village', sa.String(100), nullable=True),
        sa.Column('taluk', sa.String(100), nullable=True),
        sa.Column('district', sa.String(100), nullable=True),
        sa.Column('state', sa.String(50), nullable=True),
        sa.Column('ownership_type', sa.String(50), nullable=True),
        sa.Column('patta_number', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['citizen_id'], ['citizens.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_land_record_citizen_id', 'land_records', ['citizen_id'])
    op.create_index('ix_land_record_district', 'land_records', ['district'])

    # ── digilocker_records ────────────────────────────────────────────────────
    op.create_table(
        'digilocker_records',
        sa.Column('id', sa.CHAR(36), nullable=False),
        sa.Column('citizen_id', sa.CHAR(36), nullable=False),
        sa.Column('digilocker_id', sa.String(50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('sync_count', sa.String(10), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('citizen_id', name='uq_digilocker_citizen_id'),
        sa.UniqueConstraint('digilocker_id', name='uq_digilocker_id'),
        sa.ForeignKeyConstraint(['citizen_id'], ['citizens.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_digilocker_citizen_id', 'digilocker_records', ['citizen_id'])
    op.create_index('ix_digilocker_id', 'digilocker_records', ['digilocker_id'])

    # ── government_documents ──────────────────────────────────────────────────
    op.create_table(
        'government_documents',
        sa.Column('id', sa.CHAR(36), nullable=False),
        sa.Column('citizen_id', sa.CHAR(36), nullable=False),
        sa.Column('digilocker_record_id', sa.CHAR(36), nullable=False),
        sa.Column('document_type',
                  sa.Enum('aadhaar', 'smart_ration_card', 'income_certificate',
                          'community_certificate', 'residence_certificate',
                          'land_record', 'disability_certificate', 'farmer_id',
                          'birth_certificate', 'caste_certificate'),
                  nullable=False),
        sa.Column('document_number', sa.String(100), nullable=True),
        sa.Column('document_name', sa.String(200), nullable=False),
        sa.Column('issue_date', sa.DateTime(), nullable=True),
        sa.Column('expiry_date', sa.DateTime(), nullable=True),
        sa.Column('verification_status',
                  sa.Enum('verified', 'pending', 'expired', 'rejected'),
                  nullable=False, server_default='verified'),
        sa.Column('verified_by', sa.String(100), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('download_url', sa.String(500), nullable=True),
        sa.Column('doc_metadata', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['citizen_id'], ['citizens.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['digilocker_record_id'], ['digilocker_records.id'],
                                ondelete='CASCADE'),
    )
    op.create_index('ix_gov_doc_citizen_id', 'government_documents', ['citizen_id'])
    op.create_index('ix_gov_doc_type', 'government_documents', ['document_type'])
    op.create_index('ix_gov_doc_verification_status', 'government_documents',
                    ['verification_status'])
    op.create_index('ix_gov_doc_digilocker_record_id', 'government_documents',
                    ['digilocker_record_id'])


def downgrade() -> None:
    op.drop_index('ix_gov_doc_digilocker_record_id', 'government_documents')
    op.drop_index('ix_gov_doc_verification_status', 'government_documents')
    op.drop_index('ix_gov_doc_type', 'government_documents')
    op.drop_index('ix_gov_doc_citizen_id', 'government_documents')
    op.drop_table('government_documents')

    op.drop_index('ix_digilocker_id', 'digilocker_records')
    op.drop_index('ix_digilocker_citizen_id', 'digilocker_records')
    op.drop_table('digilocker_records')

    op.drop_index('ix_land_record_district', 'land_records')
    op.drop_index('ix_land_record_citizen_id', 'land_records')
    op.drop_table('land_records')

    op.drop_index('ix_citizen_profile_is_disabled', 'citizen_profiles')
    op.drop_index('ix_citizen_profile_is_farmer', 'citizen_profiles')
    op.drop_index('ix_citizen_profile_caste', 'citizen_profiles')
    op.drop_index('ix_citizen_profile_income_category', 'citizen_profiles')
    op.drop_index('ix_citizen_profile_sync_status', 'citizen_profiles')
    op.drop_index('ix_citizen_profile_citizen_id', 'citizen_profiles')
    op.drop_table('citizen_profiles')
