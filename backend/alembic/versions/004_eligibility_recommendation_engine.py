"""Module 4 - Eligibility & Recommendation Engine

Revision ID: 004_eligibility_recommendation_engine
Revises: 003_government_scheme_knowledge_base
"""
from alembic import op
import sqlalchemy as sa

revision = "004_eligibility_recommendation_engine"
down_revision = "003_government_scheme_knowledge_base"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "eligibility_rules",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("condition", sa.String(100), nullable=False),
        sa.Column("operator", sa.String(20), nullable=False),
        sa.Column("value", sa.JSON(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("examples", sa.JSON(), nullable=True),
        sa.Column("scope_type", sa.String(50), nullable=False, server_default="global"),
        sa.Column("scope_value", sa.String(100), nullable=True),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_eligibility_rules_code"),
    )
    op.create_index("ix_eligibility_rules_code", "eligibility_rules", ["code"])
    op.create_index("ix_eligibility_rules_condition", "eligibility_rules", ["condition"])
    op.create_index("ix_eligibility_rules_operator", "eligibility_rules", ["operator"])
    op.create_index("ix_eligibility_rules_priority", "eligibility_rules", ["priority"])
    op.create_index("ix_eligibility_rules_scope_type", "eligibility_rules", ["scope_type"])
    op.create_index("ix_eligibility_rules_scope_value", "eligibility_rules", ["scope_value"])
    op.create_index("ix_eligibility_rules_is_active", "eligibility_rules", ["is_active"])

    op.create_table(
        "recommendation_history",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("citizen_id", sa.CHAR(36), nullable=False),
        sa.Column("request_type", sa.String(30), nullable=False, server_default="generate"),
        sa.Column("query_text", sa.Text(), nullable=True),
        sa.Column("top_k", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("total_candidates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("eligible_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("overall_confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(30), nullable=False, server_default="completed"),
        sa.Column("execution_time_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("context_snapshot", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["citizen_id"], ["citizens.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_recommendation_history_citizen_id", "recommendation_history", ["citizen_id"])
    op.create_index("ix_recommendation_history_request_type", "recommendation_history", ["request_type"])
    op.create_index("ix_recommendation_history_status", "recommendation_history", ["status"])
    op.create_index("ix_recommendation_history_created_at", "recommendation_history", ["created_at"])

    op.create_table(
        "eligibility_logs",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("citizen_id", sa.CHAR(36), nullable=False),
        sa.Column("history_id", sa.CHAR(36), nullable=True),
        sa.Column("scheme_id", sa.CHAR(36), nullable=True),
        sa.Column("rule_id", sa.CHAR(36), nullable=True),
        sa.Column("rule_code", sa.String(100), nullable=True),
        sa.Column("condition", sa.String(100), nullable=False),
        sa.Column("operator", sa.String(20), nullable=False),
        sa.Column("expected_value", sa.JSON(), nullable=True),
        sa.Column("actual_value", sa.JSON(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("severity", sa.String(20), nullable=False, server_default="info"),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["citizen_id"], ["citizens.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["history_id"], ["recommendation_history.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scheme_id"], ["government_schemes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rule_id"], ["eligibility_rules.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_eligibility_logs_citizen_id", "eligibility_logs", ["citizen_id"])
    op.create_index("ix_eligibility_logs_history_id", "eligibility_logs", ["history_id"])
    op.create_index("ix_eligibility_logs_scheme_id", "eligibility_logs", ["scheme_id"])
    op.create_index("ix_eligibility_logs_rule_code", "eligibility_logs", ["rule_code"])
    op.create_index("ix_eligibility_logs_passed", "eligibility_logs", ["passed"])

    op.create_table(
        "recommendation_feedback",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("citizen_id", sa.CHAR(36), nullable=False),
        sa.Column("history_id", sa.CHAR(36), nullable=False),
        sa.Column("scheme_id", sa.CHAR(36), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_helpful", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("feedback_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="submitted"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["citizen_id"], ["citizens.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["history_id"], ["recommendation_history.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scheme_id"], ["government_schemes.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_recommendation_feedback_citizen_id", "recommendation_feedback", ["citizen_id"])
    op.create_index("ix_recommendation_feedback_history_id", "recommendation_feedback", ["history_id"])
    op.create_index("ix_recommendation_feedback_scheme_id", "recommendation_feedback", ["scheme_id"])
    op.create_index("ix_recommendation_feedback_status", "recommendation_feedback", ["status"])

    op.create_table(
        "citizen_scheme_matches",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("citizen_id", sa.CHAR(36), nullable=False),
        sa.Column("history_id", sa.CHAR(36), nullable=False),
        sa.Column("scheme_id", sa.CHAR(36), nullable=False),
        sa.Column("scheme_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("benefits", sa.Text(), nullable=True),
        sa.Column("eligibility_status", sa.String(30), nullable=False),
        sa.Column("eligibility_percentage", sa.Float(), nullable=False, server_default="0"),
        sa.Column("similarity_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("overall_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("ranking_position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recommendation_reason", sa.Text(), nullable=True),
        sa.Column("matched_rules", sa.JSON(), nullable=True),
        sa.Column("missing_requirements", sa.JSON(), nullable=True),
        sa.Column("required_documents", sa.JSON(), nullable=True),
        sa.Column("estimated_benefit", sa.String(255), nullable=True),
        sa.Column("application_ready", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("profile_match_percentage", sa.Float(), nullable=False, server_default="0"),
        sa.Column("semantic_query", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["citizen_id"], ["citizens.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["history_id"], ["recommendation_history.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scheme_id"], ["government_schemes.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_citizen_scheme_matches_citizen_id", "citizen_scheme_matches", ["citizen_id"])
    op.create_index("ix_citizen_scheme_matches_history_id", "citizen_scheme_matches", ["history_id"])
    op.create_index("ix_citizen_scheme_matches_scheme_id", "citizen_scheme_matches", ["scheme_id"])
    op.create_index("ix_citizen_scheme_matches_scheme_name", "citizen_scheme_matches", ["scheme_name"])
    op.create_index("ix_citizen_scheme_matches_eligibility_status", "citizen_scheme_matches", ["eligibility_status"])
    op.create_index("ix_citizen_scheme_matches_overall_score", "citizen_scheme_matches", ["overall_score"])
    op.create_index("ix_citizen_scheme_matches_ranking_position", "citizen_scheme_matches", ["ranking_position"])


def downgrade() -> None:
    op.drop_index("ix_citizen_scheme_matches_ranking_position", table_name="citizen_scheme_matches")
    op.drop_index("ix_citizen_scheme_matches_overall_score", table_name="citizen_scheme_matches")
    op.drop_index("ix_citizen_scheme_matches_eligibility_status", table_name="citizen_scheme_matches")
    op.drop_index("ix_citizen_scheme_matches_scheme_name", table_name="citizen_scheme_matches")
    op.drop_index("ix_citizen_scheme_matches_scheme_id", table_name="citizen_scheme_matches")
    op.drop_index("ix_citizen_scheme_matches_history_id", table_name="citizen_scheme_matches")
    op.drop_index("ix_citizen_scheme_matches_citizen_id", table_name="citizen_scheme_matches")
    op.drop_table("citizen_scheme_matches")

    op.drop_index("ix_recommendation_feedback_status", table_name="recommendation_feedback")
    op.drop_index("ix_recommendation_feedback_scheme_id", table_name="recommendation_feedback")
    op.drop_index("ix_recommendation_feedback_history_id", table_name="recommendation_feedback")
    op.drop_index("ix_recommendation_feedback_citizen_id", table_name="recommendation_feedback")
    op.drop_table("recommendation_feedback")

    op.drop_index("ix_eligibility_logs_passed", table_name="eligibility_logs")
    op.drop_index("ix_eligibility_logs_rule_code", table_name="eligibility_logs")
    op.drop_index("ix_eligibility_logs_scheme_id", table_name="eligibility_logs")
    op.drop_index("ix_eligibility_logs_history_id", table_name="eligibility_logs")
    op.drop_index("ix_eligibility_logs_citizen_id", table_name="eligibility_logs")
    op.drop_table("eligibility_logs")

    op.drop_index("ix_recommendation_history_created_at", table_name="recommendation_history")
    op.drop_index("ix_recommendation_history_status", table_name="recommendation_history")
    op.drop_index("ix_recommendation_history_request_type", table_name="recommendation_history")
    op.drop_index("ix_recommendation_history_citizen_id", table_name="recommendation_history")
    op.drop_table("recommendation_history")

    op.drop_index("ix_eligibility_rules_is_active", table_name="eligibility_rules")
    op.drop_index("ix_eligibility_rules_scope_value", table_name="eligibility_rules")
    op.drop_index("ix_eligibility_rules_scope_type", table_name="eligibility_rules")
    op.drop_index("ix_eligibility_rules_priority", table_name="eligibility_rules")
    op.drop_index("ix_eligibility_rules_operator", table_name="eligibility_rules")
    op.drop_index("ix_eligibility_rules_condition", table_name="eligibility_rules")
    op.drop_index("ix_eligibility_rules_code", table_name="eligibility_rules")
    op.drop_table("eligibility_rules")