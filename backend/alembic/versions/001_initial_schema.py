"""Initial migration - Create citizens and login_audits tables

Revision ID: 001_initial_schema
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create tables"""
    # Create citizens table
    op.create_table(
        'citizens',
        sa.Column('id', sa.CHAR(36), nullable=False),
        sa.Column('email', sa.String(254), nullable=False),
        sa.Column('phone', sa.String(20), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(100), nullable=False),
        sa.Column('gender', sa.Enum('male', 'female', 'other', 'prefer_not_to_say'), nullable=True),
        sa.Column('date_of_birth', sa.DateTime(), nullable=True),
        sa.Column('aadhaar_number', sa.String(12), nullable=True),
        sa.Column('smart_ration_card', sa.String(20), nullable=True),
        sa.Column('address_line1', sa.String(255), nullable=True),
        sa.Column('address_line2', sa.String(255), nullable=True),
        sa.Column('village', sa.String(100), nullable=True),
        sa.Column('taluk', sa.String(100), nullable=True),
        sa.Column('district', sa.String(100), nullable=False),
        sa.Column('state', sa.String(50), nullable=False),
        sa.Column('pincode', sa.String(6), nullable=True),
        sa.Column('preferred_language', sa.String(20), nullable=False, server_default='en'),
        sa.Column('profile_photo_url', sa.String(500), nullable=True),
        sa.Column('email_verified', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('email_verified_at', sa.DateTime(), nullable=True),
        sa.Column('phone_verified', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('phone_verified_at', sa.DateTime(), nullable=True),
        sa.Column('account_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('account_locked', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('last_login_ip', sa.String(45), nullable=True),
        sa.Column('status', sa.Enum('active', 'inactive', 'suspended', 'pending_verification'), nullable=False),
        sa.Column('status_reason', sa.String(255), nullable=True),
        sa.Column('digilocker_token', sa.String(500), nullable=True),
        sa.Column('digilocker_sync_at', sa.DateTime(), nullable=True),
        sa.Column('preferred_voice_language', sa.String(20), nullable=True),
        sa.Column('voice_authentication_enabled', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', sa.String(36), nullable=True),
        sa.Column('updated_by', sa.String(36), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email', name='uq_citizens_email'),
        sa.UniqueConstraint('phone', name='uq_citizens_phone'),
        sa.UniqueConstraint('aadhaar_number', name='uq_citizens_aadhaar'),
        sa.UniqueConstraint('smart_ration_card', name='uq_citizens_ration_card'),
    )
    
    # Create indexes for citizens
    op.create_index('ix_citizen_email', 'citizens', ['email'])
    op.create_index('ix_citizen_phone', 'citizens', ['phone'])
    op.create_index('ix_citizen_aadhaar_status', 'citizens', ['aadhaar_number', 'status'])
    op.create_index('ix_citizen_phone_status', 'citizens', ['phone', 'status'])
    op.create_index('ix_citizen_email_status', 'citizens', ['email', 'status'])
    op.create_index('ix_citizen_district_state', 'citizens', ['district', 'state'])
    op.create_index('ix_citizen_created_at', 'citizens', ['created_at'])
    op.create_index('ix_citizen_updated_at', 'citizens', ['updated_at'])
    op.create_index('ix_citizen_is_deleted', 'citizens', ['is_deleted'])
    
    # Create login_audits table
    op.create_table(
        'login_audits',
        sa.Column('id', sa.CHAR(36), nullable=False),
        sa.Column('citizen_id', sa.CHAR(36), nullable=False),
        sa.Column('login_type', sa.String(20), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('failure_reason', sa.String(255), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Create indexes for login_audits
    op.create_index('ix_login_audit_citizen_id', 'login_audits', ['citizen_id'])
    op.create_index('ix_login_audit_success', 'login_audits', ['success'])
    op.create_index('ix_login_audit_created_at', 'login_audits', ['created_at'])


def downgrade() -> None:
    """Drop tables"""
    op.drop_index('ix_login_audit_created_at', 'login_audits')
    op.drop_index('ix_login_audit_success', 'login_audits')
    op.drop_index('ix_login_audit_citizen_id', 'login_audits')
    op.drop_table('login_audits')
    
    op.drop_index('ix_citizen_is_deleted', 'citizens')
    op.drop_index('ix_citizen_updated_at', 'citizens')
    op.drop_index('ix_citizen_created_at', 'citizens')
    op.drop_index('ix_citizen_district_state', 'citizens')
    op.drop_index('ix_citizen_email_status', 'citizens')
    op.drop_index('ix_citizen_phone_status', 'citizens')
    op.drop_index('ix_citizen_aadhaar_status', 'citizens')
    op.drop_index('ix_citizen_aadhaar', 'citizens')
    op.drop_index('ix_citizen_phone', 'citizens')
    op.drop_index('ix_citizen_email', 'citizens')
    op.drop_table('citizens')
