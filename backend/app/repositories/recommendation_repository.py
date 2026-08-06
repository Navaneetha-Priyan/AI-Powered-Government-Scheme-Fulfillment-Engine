"""Repository layer for Module 4 eligibility and recommendation records."""
from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.exceptions.exceptions import DatabaseError, RecommendationNotFound
from app.models.recommendation import (
    CitizenSchemeMatch,
    EligibilityLog,
    EligibilityRule,
    RecommendationFeedback,
    RecommendationHistory,
)

logger = get_logger(__name__)


DEFAULT_RULES: list[dict] = [
    {
        "code": "global-income-threshold",
        "condition": "annual_income",
        "operator": "<=",
        "value": 200000,
        "priority": 10,
        "description": "Annual income should be within the lower-income threshold.",
        "examples": ["Income <= 200000", "Income under 2 lakh"],
        "scope_type": "global",
        "scope_value": None,
        "is_mandatory": True,
    },
    {
        "code": "global-age-senior",
        "condition": "age",
        "operator": ">=",
        "value": 60,
        "priority": 20,
        "description": "Senior citizen schemes require age verification.",
        "examples": ["Age >= 60"],
        "scope_type": "global",
        "scope_value": "senior citizen",
        "is_mandatory": False,
    },
    {
        "code": "global-farmer-status",
        "condition": "is_farmer",
        "operator": "==",
        "value": True,
        "priority": 30,
        "description": "Farmer-facing schemes require farmer status.",
        "examples": ["Occupation == Farmer", "Farmer == True"],
        "scope_type": "global",
        "scope_value": "farmer",
        "is_mandatory": True,
    },
    {
        "code": "global-land-area",
        "condition": "total_land_area",
        "operator": "<=",
        "value": 5,
        "priority": 40,
        "description": "Landholding-based schemes often target small and marginal farmers.",
        "examples": ["LandArea < 5 Acres"],
        "scope_type": "global",
        "scope_value": "agriculture",
        "is_mandatory": True,
    },
    {
        "code": "global-disabled-status",
        "condition": "is_disabled",
        "operator": "==",
        "value": True,
        "priority": 50,
        "description": "Disability-linked schemes require disability status.",
        "examples": ["Disabled == True"],
        "scope_type": "global",
        "scope_value": "disability",
        "is_mandatory": False,
    },
    {
        "code": "global-state-tamil-nadu",
        "condition": "state",
        "operator": "==",
        "value": "Tamil Nadu",
        "priority": 60,
        "description": "State-specific schemes can require residency in Tamil Nadu.",
        "examples": ["State == Tamil Nadu"],
        "scope_type": "state",
        "scope_value": "Tamil Nadu",
        "is_mandatory": False,
    },
    {
        "code": "global-bpl-status",
        "condition": "is_bpl",
        "operator": "==",
        "value": True,
        "priority": 70,
        "description": "BPL schemes require BPL classification.",
        "examples": ["BPL == True"],
        "scope_type": "global",
        "scope_value": "bpl",
        "is_mandatory": False,
    },
]


class EligibilityRuleRepository:
    def __init__(self, db: Session):
        self.db = db

    def seed_defaults(self) -> list[EligibilityRule]:
        try:
            existing = self.db.query(EligibilityRule).count()
            if existing:
                return self.list_active()

            rules = [EligibilityRule(**payload) for payload in DEFAULT_RULES]
            self.db.add_all(rules)
            self.db.commit()
            for rule in rules:
                self.db.refresh(rule)
            logger.info("Seeded default eligibility rules: %s", len(rules))
            return rules
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError(f"Failed to seed eligibility rules: {exc}") from exc

    def create(self, data: dict) -> EligibilityRule:
        try:
            item = EligibilityRule(**data)
            self.db.add(item)
            self.db.commit()
            self.db.refresh(item)
            return item
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError(f"Failed to create eligibility rule: {exc}") from exc

    def list_active(self) -> list[EligibilityRule]:
        try:
            return (
                self.db.query(EligibilityRule)
                .filter(EligibilityRule.is_active == True)  # noqa: E712
                .order_by(EligibilityRule.priority.asc(), EligibilityRule.created_at.asc())
                .all()
            )
        except Exception as exc:
            raise DatabaseError(f"Failed to fetch eligibility rules: {exc}") from exc

    def list_for_scope(self, scope_type: str | None = None, scope_value: str | None = None) -> list[EligibilityRule]:
        query = self.db.query(EligibilityRule).filter(EligibilityRule.is_active == True)  # noqa: E712
        if scope_type:
            query = query.filter(EligibilityRule.scope_type == scope_type)
        if scope_value:
            query = query.filter(EligibilityRule.scope_value == scope_value)
        return query.order_by(EligibilityRule.priority.asc(), EligibilityRule.created_at.asc()).all()


class RecommendationHistoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> RecommendationHistory:
        try:
            item = RecommendationHistory(**data)
            self.db.add(item)
            self.db.commit()
            self.db.refresh(item)
            return item
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError(f"Failed to create recommendation history: {exc}") from exc

    def update(self, history: RecommendationHistory, data: dict) -> RecommendationHistory:
        try:
            for key, value in data.items():
                if hasattr(history, key):
                    setattr(history, key, value)
            self.db.commit()
            self.db.refresh(history)
            return history
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError(f"Failed to update recommendation history: {exc}") from exc

    def get(self, history_id: str) -> RecommendationHistory:
        history = self.db.query(RecommendationHistory).filter(RecommendationHistory.id == history_id).first()
        if not history:
            raise RecommendationNotFound(history_id)
        return history

    def get_for_citizen(self, citizen_id: str, limit: int = 10) -> list[RecommendationHistory]:
        return (
            self.db.query(RecommendationHistory)
            .filter(RecommendationHistory.citizen_id == citizen_id)
            .order_by(RecommendationHistory.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_latest_for_citizen(self, citizen_id: str) -> Optional[RecommendationHistory]:
        return (
            self.db.query(RecommendationHistory)
            .filter(RecommendationHistory.citizen_id == citizen_id)
            .order_by(RecommendationHistory.created_at.desc())
            .first()
        )


class RecommendationMatchRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_many(self, items: Iterable[dict]) -> list[CitizenSchemeMatch]:
        try:
            records = [CitizenSchemeMatch(**item) for item in items]
            self.db.add_all(records)
            self.db.commit()
            for record in records:
                self.db.refresh(record)
            return records
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError(f"Failed to persist recommendation matches: {exc}") from exc

    def list_for_citizen(self, citizen_id: str, limit: int = 20) -> list[CitizenSchemeMatch]:
        return (
            self.db.query(CitizenSchemeMatch)
            .filter(CitizenSchemeMatch.citizen_id == citizen_id)
            .order_by(CitizenSchemeMatch.created_at.desc())
            .limit(limit)
            .all()
        )

    def get(self, match_id: str) -> Optional[CitizenSchemeMatch]:
        return self.db.query(CitizenSchemeMatch).filter(CitizenSchemeMatch.id == match_id).first()

    def list_for_history(self, history_id: str) -> list[CitizenSchemeMatch]:
        return (
            self.db.query(CitizenSchemeMatch)
            .filter(CitizenSchemeMatch.history_id == history_id)
            .order_by(CitizenSchemeMatch.ranking_position.asc())
            .all()
        )


class EligibilityLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_many(self, items: Iterable[dict]) -> list[EligibilityLog]:
        try:
            records = [EligibilityLog(**item) for item in items]
            self.db.add_all(records)
            self.db.commit()
            for record in records:
                self.db.refresh(record)
            return records
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError(f"Failed to persist eligibility logs: {exc}") from exc

    def list_for_history(self, history_id: str) -> list[EligibilityLog]:
        return (
            self.db.query(EligibilityLog)
            .filter(EligibilityLog.history_id == history_id)
            .order_by(EligibilityLog.created_at.asc())
            .all()
        )


class RecommendationFeedbackRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> RecommendationFeedback:
        try:
            item = RecommendationFeedback(**data)
            self.db.add(item)
            self.db.commit()
            self.db.refresh(item)
            return item
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError(f"Failed to create recommendation feedback: {exc}") from exc

    def list_for_citizen(self, citizen_id: str, limit: int = 20) -> list[RecommendationFeedback]:
        return (
            self.db.query(RecommendationFeedback)
            .filter(RecommendationFeedback.citizen_id == citizen_id)
            .order_by(RecommendationFeedback.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_by_history_and_scheme(self, citizen_id: str, history_id: str, scheme_id: str) -> Optional[RecommendationFeedback]:
        return (
            self.db.query(RecommendationFeedback)
            .filter(
                RecommendationFeedback.citizen_id == citizen_id,
                RecommendationFeedback.history_id == history_id,
                RecommendationFeedback.scheme_id == scheme_id,
            )
            .first()
        )


class RecommendationRepository:
    def __init__(self, db: Session):
        self.db = db
        self.rule_repo = EligibilityRuleRepository(db)
        self.history_repo = RecommendationHistoryRepository(db)
        self.match_repo = RecommendationMatchRepository(db)
        self.log_repo = EligibilityLogRepository(db)
        self.feedback_repo = RecommendationFeedbackRepository(db)

    def get_history(self, history_id: str, citizen_id: str | None = None) -> RecommendationHistory:
        history = self.history_repo.get(history_id)
        if citizen_id and history.citizen_id != citizen_id:
            raise RecommendationNotFound(history_id)
        return history

    def count_history(self, citizen_id: str) -> int:
        try:
            return int(
                self.db.query(func.count(RecommendationHistory.id))
                .filter(RecommendationHistory.citizen_id == citizen_id)
                .scalar()
                or 0
            )
        except Exception as exc:
            raise DatabaseError(f"Failed to count recommendation history: {exc}") from exc