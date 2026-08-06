"""Module 3 government scheme knowledge base.

Revision ID: 003_government_scheme_knowledge_base
Revises: 002_citizen_profile_digilocker
"""
from alembic import op
import sqlalchemy as sa
revision='003_government_scheme_knowledge_base'
down_revision='002_citizen_profile_digilocker'
branch_labels=None
depends_on=None
def upgrade():
    op.create_table('government_schemes',sa.Column('id',sa.CHAR(36),primary_key=True),sa.Column('scheme_name',sa.String(255),nullable=False,unique=True),sa.Column('description',sa.Text(),nullable=False),sa.Column('category',sa.String(100),nullable=False),sa.Column('department',sa.String(150),nullable=False),sa.Column('government_level',sa.String(30),nullable=False),sa.Column('state',sa.String(100)),sa.Column('benefits',sa.Text()),sa.Column('eligibility_summary',sa.Text()),sa.Column('required_documents',sa.Text()),sa.Column('application_process',sa.Text()),sa.Column('official_link',sa.String(500)),sa.Column('language',sa.String(20),nullable=False),sa.Column('status',sa.String(20),nullable=False),sa.Column('is_deleted',sa.Boolean(),nullable=False),sa.Column('created_at',sa.DateTime(),nullable=False),sa.Column('updated_at',sa.DateTime()))
    op.create_index('ix_government_schemes_category','government_schemes',['category']);op.create_index('ix_government_schemes_department','government_schemes',['department'])
    op.create_table('scheme_documents',sa.Column('id',sa.CHAR(36),primary_key=True),sa.Column('scheme_id',sa.CHAR(36),sa.ForeignKey('government_schemes.id',ondelete='CASCADE'),nullable=False),sa.Column('file_name',sa.String(255),nullable=False),sa.Column('file_path',sa.String(500),nullable=False),sa.Column('file_size',sa.Integer(),nullable=False),sa.Column('uploaded_by',sa.CHAR(36)),sa.Column('version',sa.Integer(),nullable=False),sa.Column('processing_status',sa.String(20),nullable=False),sa.Column('processing_error',sa.Text()),sa.Column('created_at',sa.DateTime(),nullable=False),sa.Column('updated_at',sa.DateTime()))
    op.create_table('scheme_chunks',sa.Column('id',sa.CHAR(36),primary_key=True),sa.Column('scheme_id',sa.CHAR(36),sa.ForeignKey('government_schemes.id',ondelete='CASCADE'),nullable=False),sa.Column('document_id',sa.CHAR(36),sa.ForeignKey('scheme_documents.id',ondelete='CASCADE'),nullable=False),sa.Column('chunk_text',sa.Text(),nullable=False),sa.Column('page_number',sa.Integer(),nullable=False),sa.Column('section_name',sa.String(150)),sa.Column('embedding_id',sa.String(100),nullable=False,unique=True),sa.Column('token_count',sa.Integer(),nullable=False),sa.Column('created_at',sa.DateTime(),nullable=False))
def downgrade():
    op.drop_table('scheme_chunks');op.drop_table('scheme_documents');op.drop_index('ix_government_schemes_department','government_schemes');op.drop_index('ix_government_schemes_category','government_schemes');op.drop_table('government_schemes')
