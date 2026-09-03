"""Allow every persisted document-processing status in MySQL.

Older local databases were created from an early SQLAlchemy model where
``upload_status`` was a MySQL ENUM without ``needs_review``.  The extraction
service then successfully extracted fields but failed while saving that status.
"""
from alembic import op
import sqlalchemy as sa


revision = "006_document_status_enum"
down_revision = "005_citizen_document_intelligence"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        op.execute(
            "ALTER TABLE uploaded_documents MODIFY COLUMN upload_status "
            "ENUM('uploaded','processing','processed','needs_review','verified','failed') "
            "NOT NULL DEFAULT 'uploaded'"
        )


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        # Preserve existing review rows before removing the enum member.
        op.execute("UPDATE uploaded_documents SET upload_status='processed' WHERE upload_status='needs_review'")
        op.execute(
            "ALTER TABLE uploaded_documents MODIFY COLUMN upload_status "
            "ENUM('uploaded','processing','processed','verified','failed') "
            "NOT NULL DEFAULT 'uploaded'"
        )
