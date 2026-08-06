"""SQLAlchemy models for Module 4 eligibility and recommendations."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CHAR,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database.connection import Base


class EligibilityRule(Base):
    __tablename__ = "eligibility_rules"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    code = Column(String(100), nullable=False, unique=True, index=True)
    condition = Column(String(100), nullable=False, index=True)
    operator = Column(String(20), nullable=False, index=True)
    value = Column(JSON, nullable=True)
    priority = Column(Integer, nullable=False, default=100, index=True)
    description = Column(Text, nullable=True)
    examples = Column(JSON, nullable=True)
    scope_type = Column(String(50), nullable=False, default="global", index=True)
    scope_value = Column(String(100), nullable=True, index=True)
    is_mandatory = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_eligibility_rules_scope_priority", "scope_type", "scope_value", "priority"),
        Index("ix_eligibility_rules_active_priority", "is_active", "priority"),
    )


class RecommendationHistory(Base):
    __tablename__ = "recommendation_history"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    citizen_id = Column(CHAR(36), ForeignKey("citizens.id", ondelete="CASCADE"), nullable=False, index=True)
    request_type = Column(String(30), nullable=False, default="generate", index=True)
    query_text = Column(Text, nullable=True)
    top_k = Column(Integer, nullable=False, default=5)
    total_candidates = Column(Integer, nullable=False, default=0)
    eligible_count = Column(Integer, nullable=False, default=0)
    overall_confidence = Column(Float, nullable=False, default=0.0)
    status = Column(String(30), nullable=False, default="completed")
    execution_time_ms = Column(Integer, nullable=False, default=0)
    context_snapshot = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)

    matches = relationship("CitizenSchemeMatch", back_populates="history", cascade="all, delete-orphan")
    logs = relationship("EligibilityLog", back_populates="history", cascade="all, delete-orphan")
    feedback = relationship("RecommendationFeedback", back_populates="history", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_recommendation_history_citizen_created", "citizen_id", "created_at"),
    )


class EligibilityLog(Base):
    __tablename__ = "eligibility_logs"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    citizen_id = Column(CHAR(36), ForeignKey("citizens.id", ondelete="CASCADE"), nullable=False, index=True)
    history_id = Column(CHAR(36), ForeignKey("recommendation_history.id", ondelete="CASCADE"), nullable=True, index=True)
    scheme_id = Column(CHAR(36), ForeignKey("government_schemes.id", ondelete="CASCADE"), nullable=True, index=True)
    rule_id = Column(CHAR(36), ForeignKey("eligibility_rules.id", ondelete="SET NULL"), nullable=True, index=True)
    rule_code = Column(String(100), nullable=True, index=True)
    condition = Column(String(100), nullable=False)
    operator = Column(String(20), nullable=False)
    expected_value = Column(JSON, nullable=True)
    actual_value = Column(JSON, nullable=True)
    passed = Column(Boolean, nullable=False, default=False, index=True)
    severity = Column(String(20), nullable=False, default="info")
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    history = relationship("RecommendationHistory", back_populates="logs")

    __table_args__ = (
        Index("ix_eligibility_logs_history_rule", "history_id", "rule_code"),
    )


class RecommendationFeedback(Base):
    __tablename__ = "recommendation_feedback"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    citizen_id = Column(CHAR(36), ForeignKey("citizens.id", ondelete="CASCADE"), nullable=False, index=True)
    history_id = Column(CHAR(36), ForeignKey("recommendation_history.id", ondelete="CASCADE"), nullable=False, index=True)
    scheme_id = Column(CHAR(36), ForeignKey("government_schemes.id", ondelete="CASCADE"), nullable=False, index=True)
    rating = Column(Integer, nullable=False, default=0)
    is_helpful = Column(Boolean, nullable=False, default=False)
    feedback_text = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="submitted", index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)

    history = relationship("RecommendationHistory", back_populates="feedback")

    __table_args__ = (
        Index("ix_recommendation_feedback_citizen_scheme", "citizen_id", "scheme_id"),
    )


class CitizenSchemeMatch(Base):
    __tablename__ = "citizen_scheme_matches"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    citizen_id = Column(CHAR(36), ForeignKey("citizens.id", ondelete="CASCADE"), nullable=False, index=True)
    history_id = Column(CHAR(36), ForeignKey("recommendation_history.id", ondelete="CASCADE"), nullable=False, index=True)
    scheme_id = Column(CHAR(36), ForeignKey("government_schemes.id", ondelete="CASCADE"), nullable=False, index=True)
    scheme_name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    benefits = Column(Text, nullable=True)
    eligibility_status = Column(String(30), nullable=False, index=True)
    eligibility_percentage = Column(Float, nullable=False, default=0.0)
    similarity_score = Column(Float, nullable=False, default=0.0)
    confidence_score = Column(Float, nullable=False, default=0.0)
    overall_score = Column(Float, nullable=False, default=0.0, index=True)
    ranking_position = Column(Integer, nullable=False, default=0, index=True)
    recommendation_reason = Column(Text, nullable=True)
    matched_rules = Column(JSON, nullable=True)
    missing_requirements = Column(JSON, nullable=True)
    required_documents = Column(JSON, nullable=True)
    estimated_benefit = Column(String(255), nullable=True)
    application_ready = Column(Boolean, nullable=False, default=False, index=True)
    profile_match_percentage = Column(Float, nullable=False, default=0.0)
    semantic_query = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)

    history = relationship("RecommendationHistory", back_populates="matches")

    __table_args__ = (
        Index("ix_citizen_scheme_matches_citizen_history", "citizen_id", "history_id"),
        Index("ix_citizen_scheme_matches_citizen_rank", "citizen_id", "ranking_position"),
        Index("ix_citizen_scheme_matches_scheme", "scheme_id"),
    )