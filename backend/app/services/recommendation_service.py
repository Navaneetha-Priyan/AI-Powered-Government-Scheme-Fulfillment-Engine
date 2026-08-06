"""Module 4 eligibility, semantic search, ranking, and recommendation services."""
from __future__ import annotations

import math
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Iterable, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.exceptions.exceptions import (
    EligibilityEngineError,
    InternalServerError,
    KnowledgeBaseUnavailable,
    NotFoundError,
    ProfileNotFoundError,
    RecommendationGenerationError,
    RecommendationNotFound,
    RuleEvaluationError,
)
from app.models.government_scheme import GovernmentScheme
from app.models.recommendation import CitizenSchemeMatch, EligibilityRule, RecommendationFeedback, RecommendationHistory
from app.repositories.citizen_profile_repository import CitizenProfileRepository, LandRecordRepository
from app.repositories.citizen_repository import CitizenRepository
from app.repositories.digilocker_repository import GovernmentDocumentRepository
from app.repositories.government_scheme_repository import GovernmentSchemeRepository
from app.repositories.recommendation_repository import (
    EligibilityLogRepository,
    EligibilityRuleRepository,
    RecommendationFeedbackRepository,
    RecommendationHistoryRepository,
    RecommendationMatchRepository,
    RecommendationRepository,
)
from app.schemas.recommendation import (
    EligibilityCheckResponse,
    EligibilityPreviewResponse,
    RecommendationHistoryResponse,
    RecommendationListResponse,
    RecommendationMatchResponse,
    RecommendationSummaryResponse,
)
from app.services.government_scheme_service import GovernmentSchemeService

logger = get_logger(__name__)


@dataclass
class CitizenContext:
    citizen: Any
    profile: Any
    land_records: list[Any]
    documents: list[Any]
    total_land_area: float
    profile_completion_percentage: int
    age: Optional[int]
    senior_citizen: bool
    family_size: Optional[int]
    document_types: set[str] = field(default_factory=set)
    document_names: set[str] = field(default_factory=set)

    @property
    def state(self) -> str:
        return getattr(self.citizen, "state", "") or ""

    @property
    def district(self) -> str:
        return getattr(self.citizen, "district", "") or ""

    @property
    def village(self) -> str:
        return getattr(self.citizen, "village", "") or ""

    @property
    def income(self) -> float:
        return float(getattr(self.profile, "annual_income", 0.0) or 0.0)

    @property
    def is_farmer(self) -> bool:
        return bool(getattr(self.profile, "is_farmer", False)) or self._match_text("farmer", self.occupation)

    @property
    def occupation(self) -> str:
        return getattr(self.profile, "occupation", "") or ""

    @property
    def caste(self) -> str:
        return getattr(self.profile, "caste", "") or ""

    @property
    def community(self) -> str:
        return getattr(self.profile, "community", "") or ""

    @property
    def is_disabled(self) -> bool:
        return bool(getattr(self.profile, "is_disabled", False))

    @property
    def marital_status(self) -> str:
        return str(getattr(self.profile, "marital_status", "") or "")

    @property
    def education_level(self) -> str:
        return getattr(self.profile, "education_level", "") or ""

    @property
    def family_income(self) -> float:
        return self.income

    @property
    def is_bpl(self) -> bool:
        income_category = str(getattr(self.profile, "income_category", "") or "").lower()
        return income_category == "bpl" or self.income <= 200000

    @property
    def has_documents(self) -> bool:
        return bool(self.document_types)

    def _match_text(self, needle: str, haystack: str) -> bool:
        return needle.lower() in (haystack or "").lower()

    def to_snapshot(self) -> dict[str, Any]:
        return {
            "citizen_id": getattr(self.citizen, "id", None),
            "full_name": getattr(self.citizen, "full_name", None),
            "state": self.state,
            "district": self.district,
            "village": self.village,
            "occupation": self.occupation,
            "income": self.income,
            "is_farmer": self.is_farmer,
            "is_disabled": self.is_disabled,
            "family_size": self.family_size,
            "profile_completion_percentage": self.profile_completion_percentage,
            "document_types": sorted(self.document_types),
            "total_land_area": self.total_land_area,
            "age": self.age,
            "senior_citizen": self.senior_citizen,
        }

    def to_query_text(self) -> str:
        parts = [
            self.occupation,
            self.state,
            self.district,
            self.village,
            "farmer" if self.is_farmer else "",
            "disabled" if self.is_disabled else "",
            "senior citizen" if self.senior_citizen else "",
            "bpl" if self.is_bpl else "",
            "agriculture" if self.total_land_area else "",
            self.caste,
            self.community,
            self.education_level,
            " ".join(sorted(self.document_types)),
        ]
        return " ".join(part for part in parts if part).strip()


@dataclass
class RuleDefinition:
    code: str
    condition: str
    operator: str
    value: Any = None
    priority: int = 100
    description: str | None = None
    examples: Any = None
    scope_type: str = "global"
    scope_value: str | None = None
    is_mandatory: bool = True
    source: str = "configured"

    @classmethod
    def from_rule_model(cls, rule: EligibilityRule) -> "RuleDefinition":
        return cls(
            code=rule.code,
            condition=rule.condition,
            operator=rule.operator,
            value=rule.value,
            priority=rule.priority,
            description=rule.description,
            examples=rule.examples,
            scope_type=rule.scope_type,
            scope_value=rule.scope_value,
            is_mandatory=rule.is_mandatory,
            source="database",
        )


@dataclass
class RuleEvaluation:
    rule: RuleDefinition
    passed: bool
    actual_value: Any
    expected_value: Any
    severity: str = "info"
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class SchemeCandidate:
    scheme: GovernmentScheme
    semantic_score: float
    chunks: list[dict[str, Any]] = field(default_factory=list)
    aggregated_text: str = ""


@dataclass
class SchemeRecommendation:
    scheme: GovernmentScheme
    eligibility_status: str
    eligibility_percentage: float
    similarity_score: float
    confidence_score: float
    overall_score: float
    ranking_position: int
    recommendation_reason: str
    matched_rules: list[dict[str, Any]]
    missing_requirements: list[dict[str, Any]]
    required_documents: list[str]
    estimated_benefit: str | None
    application_ready: bool
    profile_match_percentage: float
    semantic_query: str
    candidate_chunks: list[dict[str, Any]] = field(default_factory=list)

    def to_match_payload(self, citizen_id: str, history_id: str) -> dict[str, Any]:
        return {
            "citizen_id": citizen_id,
            "history_id": history_id,
            "scheme_id": self.scheme.id,
            "scheme_name": self.scheme.scheme_name,
            "description": self.scheme.description,
            "benefits": self.scheme.benefits,
            "eligibility_status": self.eligibility_status,
            "eligibility_percentage": self.eligibility_percentage,
            "similarity_score": self.similarity_score,
            "confidence_score": self.confidence_score,
            "overall_score": self.overall_score,
            "ranking_position": self.ranking_position,
            "recommendation_reason": self.recommendation_reason,
            "matched_rules": self.matched_rules,
            "missing_requirements": self.missing_requirements,
            "required_documents": self.required_documents,
            "estimated_benefit": self.estimated_benefit,
            "application_ready": self.application_ready,
            "profile_match_percentage": self.profile_match_percentage,
            "semantic_query": self.semantic_query,
        }


class CitizenContextService:
    def __init__(self, db: Session):
        self.db = db
        self.citizen_repo = CitizenRepository(db)
        self.profile_repo = CitizenProfileRepository(db)
        self.land_repo = LandRecordRepository(db)
        self.document_repo = GovernmentDocumentRepository(db)

    def build(self, citizen_id: str) -> CitizenContext:
        citizen = self.citizen_repo.get_by_id(citizen_id)
        if not citizen:
            raise NotFoundError("Citizen not found", resource="citizen")

        profile = self.profile_repo.get_by_citizen_id(citizen_id)
        if not profile:
            raise ProfileNotFoundError(citizen_id)

        land_records = self.land_repo.get_by_citizen_id(citizen_id)
        documents = self.document_repo.get_by_citizen_id(citizen_id)
        total_land_area = self.land_repo.get_total_area(citizen_id)
        age = self._calculate_age(getattr(citizen, "date_of_birth", None))
        document_types = {str(getattr(document, "document_type", "")).lower() for document in documents}
        document_names = {str(getattr(document, "document_name", "")).lower() for document in documents}
        profile_completion = int(getattr(profile, "profile_completion_percentage", 0) or 0)

        return CitizenContext(
            citizen=citizen,
            profile=profile,
            land_records=land_records,
            documents=documents,
            total_land_area=total_land_area,
            profile_completion_percentage=profile_completion,
            age=age,
            senior_citizen=bool(age is not None and age >= 60),
            family_size=getattr(profile, "family_member_count", None),
            document_types=document_types,
            document_names=document_names,
        )

    def _calculate_age(self, date_of_birth: Any) -> Optional[int]:
        if not date_of_birth:
            return None
        if isinstance(date_of_birth, str):
            try:
                date_of_birth = datetime.fromisoformat(date_of_birth)
            except ValueError:
                return None
        today = datetime.utcnow().date()
        years = today.year - date_of_birth.date().year - ((today.month, today.day) < (date_of_birth.date().month, date_of_birth.date().day))
        return years


class RuleEvaluationService:
    OPERATORS = {"==", "=", "!=", ">", ">=", "<", "<=", "in", "not_in", "contains", "not_contains", "exists", "not_exists"}

    def evaluate(self, context: CitizenContext, rule: RuleDefinition) -> RuleEvaluation:
        try:
            actual_value = self._resolve_context_value(context, rule.condition)
            passed = self._compare(actual_value, rule.operator, rule.value)
            details = {
                "condition": rule.condition,
                "operator": rule.operator,
                "expected": rule.value,
                "actual": actual_value,
                "source": rule.source,
            }
            return RuleEvaluation(rule=rule, passed=passed, actual_value=actual_value, expected_value=rule.value, severity="high" if rule.is_mandatory and not passed else "info", details=details)
        except Exception as exc:
            raise RuleEvaluationError(str(exc)) from exc

    def evaluate_many(self, context: CitizenContext, rules: Iterable[RuleDefinition]) -> list[RuleEvaluation]:
        return [self.evaluate(context, rule) for rule in sorted(rules, key=lambda item: item.priority)]

    def _resolve_context_value(self, context: CitizenContext, field_name: str) -> Any:
        normalized = field_name.replace(" ", "_").lower()
        mapping = {
            "age": context.age,
            "gender": getattr(context.citizen, "gender", None),
            "annual_income": context.income,
            "family_income": context.family_income,
            "occupation": context.occupation,
            "is_farmer": context.is_farmer,
            "farmer": context.is_farmer,
            "land_ownership": bool(context.total_land_area > 0),
            "land_area": context.total_land_area,
            "total_land_area": context.total_land_area,
            "land_size": context.total_land_area,
            "land_type": getattr(context.land_records[0], "land_type", None) if context.land_records else None,
            "is_disabled": context.is_disabled,
            "disabled": context.is_disabled,
            "community": context.community,
            "caste": context.caste,
            "sub_caste": getattr(context.profile, "sub_caste", None),
            "minority_status": self._match_text("minority", context.community) or self._match_text("minority", context.caste),
            "marital_status": context.marital_status,
            "education": context.education_level,
            "state": context.state,
            "district": context.district,
            "village": context.village,
            "student_status": self._match_text("student", context.education_level),
            "employment_status": self._derive_employment_status(context),
            "government_employee_status": self._match_text("government", context.occupation) or self._match_text("govt", context.occupation),
            "widow_status": self._match_text("widow", context.marital_status),
            "senior_citizen": context.senior_citizen,
            "bpl": context.is_bpl,
            "is_bpl": context.is_bpl,
            "family_size": context.family_size,
            "profile_completeness": context.profile_completion_percentage,
            "profile_completion": context.profile_completion_percentage,
            "required_documents": sorted(context.document_types),
            "existing_benefits": sorted(context.document_types),
            "has_documents": context.has_documents,
        }
        if normalized in mapping:
            return mapping[normalized]
        if hasattr(context.profile, normalized):
            return getattr(context.profile, normalized)
        if hasattr(context.citizen, normalized):
            return getattr(context.citizen, normalized)
        return None

    def _compare(self, actual_value: Any, operator: str, expected_value: Any) -> bool:
        operator = operator.lower().strip()
        if operator not in self.OPERATORS:
            raise RuleEvaluationError(f"Unsupported operator: {operator}")

        if operator in {"exists", "not_exists"}:
            present = actual_value not in {None, "", [], {}, ()}
            return present if operator == "exists" else not present

        if operator in {"contains", "not_contains"}:
            actual_text = _normalize_text(actual_value)
            expected_text = _normalize_text(expected_value)
            result = expected_text in actual_text
            return result if operator == "contains" else not result

        if operator in {"in", "not_in"}:
            if isinstance(expected_value, (list, tuple, set)):
                result = actual_value in expected_value
            else:
                result = actual_value in {_normalize_text(expected_value), expected_value}
            return result if operator == "in" else not result

        actual_number = _coerce_number(actual_value)
        expected_number = _coerce_number(expected_value)
        if actual_number is not None and expected_number is not None:
            if operator in {"=", "=="}:
                return actual_number == expected_number
            if operator == "!=":
                return actual_number != expected_number
            if operator == ">":
                return actual_number > expected_number
            if operator == ">=":
                return actual_number >= expected_number
            if operator == "<":
                return actual_number < expected_number
            if operator == "<=":
                return actual_number <= expected_number

        actual_bool = _coerce_bool(actual_value)
        expected_bool = _coerce_bool(expected_value)
        if actual_bool is not None and expected_bool is not None:
            if operator in {"=", "=="}:
                return actual_bool == expected_bool
            if operator == "!=":
                return actual_bool != expected_bool

        actual_text = _normalize_text(actual_value)
        expected_text = _normalize_text(expected_value)
        if operator in {"=", "=="}:
            return actual_text == expected_text
        if operator == "!=":
            return actual_text != expected_text
        if operator == "contains":
            return expected_text in actual_text
        if operator == "not_contains":
            return expected_text not in actual_text

        return False

    def _derive_employment_status(self, context: CitizenContext) -> str:
        occupation = _normalize_text(context.occupation)
        if not occupation:
            return "unknown"
        if "farmer" in occupation:
            return "farmer"
        if any(token in occupation for token in ["student", "scholar"]):
            return "student"
        if any(token in occupation for token in ["unemployed", "jobless"]):
            return "unemployed"
        if any(token in occupation for token in ["government", "govt"]):
            return "government_employee"
        return occupation

    def _match_text(self, needle: str, haystack: str) -> bool:
        return needle.lower() in _normalize_text(haystack)


class SimilarityService:
    def __init__(self, search_fn: Callable[..., list[dict[str, Any]]] | None = None):
        self.search_fn = search_fn

    def build_query(self, context: CitizenContext, category: str | None = None, state: str | None = None) -> str:
        parts = [context.to_query_text()]
        if category:
            parts.append(category)
        if state:
            parts.append(state)
        return " ".join(part for part in parts if part).strip()

    def search(self, query: str, limit: int, category: str | None = None) -> list[dict[str, Any]]:
        if not self.search_fn:
            raise KnowledgeBaseUnavailable("Semantic search service is not configured")
        try:
            return self.search_fn(query, limit, category)
        except Exception as exc:
            raise KnowledgeBaseUnavailable(str(exc)) from exc

    def group_candidates(self, scheme_results: list[dict[str, Any]]) -> list[SchemeCandidate]:
        grouped: dict[str, dict[str, Any]] = defaultdict(lambda: {"chunks": [], "score": 0.0, "scheme": None})
        for item in scheme_results:
            scheme_id = item.get("scheme_id")
            if not scheme_id:
                continue
            entry = grouped[scheme_id]
            entry["score"] = max(float(entry["score"]), float(item.get("similarity_score", 0.0) or 0.0))
            entry["chunks"].append(item)
            if entry["scheme"] is None:
                entry["scheme"] = item

        candidates: list[SchemeCandidate] = []
        for scheme_id, payload in grouped.items():
            first = payload["scheme"] or {}
            scheme = first.get("scheme_object")
            if not scheme:
                continue
            text = " ".join(chunk.get("matched_content") or chunk.get("relevant_content") or "" for chunk in payload["chunks"])
            candidates.append(
                SchemeCandidate(
                    scheme=scheme,
                    semantic_score=float(payload["score"]),
                    chunks=payload["chunks"],
                    aggregated_text=text.strip(),
                )
            )
        return candidates


class ExplanationService:
    def build(self, context: CitizenContext, evaluation: list[RuleEvaluation], candidate: SchemeCandidate, required_documents: list[str], estimated_benefit: str | None) -> str:
        matched = [item.rule.condition for item in evaluation if item.passed and item.rule.is_mandatory]
        missing = [item.rule.condition for item in evaluation if not item.passed and item.rule.is_mandatory]
        fragments = [f"{candidate.scheme.scheme_name}: {'Eligible' if not missing else 'Not fully eligible'}"]
        if matched:
            fragments.append("Matched: " + ", ".join(matched[:5]))
        if missing:
            fragments.append("Missing: " + ", ".join(missing[:5]))
        if required_documents:
            fragments.append("Documents: " + ", ".join(required_documents[:5]))
        if estimated_benefit:
            fragments.append(f"Benefit: {estimated_benefit}")
        fragments.append(f"Similarity Score {round(candidate.semantic_score * 100, 1)}%")
        return " | ".join(fragments)


class RankingService:
    def score(
        self,
        eligibility_percentage: float,
        similarity_score: float,
        benefit_score: float,
        profile_match_percentage: float,
        document_score: float,
        state_bonus: float = 0.0,
        recency_bonus: float = 0.0,
    ) -> float:
        overall = (
            eligibility_percentage * settings.RECOMMENDATION_ELIGIBILITY_WEIGHT
            + similarity_score * settings.RECOMMENDATION_SIMILARITY_WEIGHT
            + benefit_score * settings.RECOMMENDATION_BENEFIT_WEIGHT
            + profile_match_percentage * settings.RECOMMENDATION_PROFILE_WEIGHT
            + document_score * settings.RECOMMENDATION_DOCUMENT_WEIGHT
            + state_bonus
            + recency_bonus
        )
        return round(max(0.0, min(100.0, overall)), 2)

    def confidence(self, eligibility_percentage: float, similarity_score: float, document_score: float, profile_match_percentage: float) -> float:
        return round(max(0.0, min(100.0, (eligibility_percentage * 0.45) + (similarity_score * 0.3) + (document_score * 0.1) + (profile_match_percentage * 0.15))), 2)


class RecommendationHistoryService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = RecommendationRepository(db)

    def create_history(self, citizen_id: str, request_type: str, query_text: str, top_k: int, total_candidates: int, eligible_count: int, confidence: float, context_snapshot: dict[str, Any], execution_time_ms: int, status: str = "completed", notes: str | None = None) -> RecommendationHistory:
        return self.repo.history_repo.create(
            {
                "citizen_id": citizen_id,
                "request_type": request_type,
                "query_text": query_text,
                "top_k": top_k,
                "total_candidates": total_candidates,
                "eligible_count": eligible_count,
                "overall_confidence": confidence,
                "status": status,
                "execution_time_ms": execution_time_ms,
                "context_snapshot": context_snapshot,
                "notes": notes,
                "completed_at": datetime.utcnow(),
            }
        )

    def add_matches(self, history_id: str, citizen_id: str, recommendations: list[SchemeRecommendation]) -> list[CitizenSchemeMatch]:
        payloads = [recommendation.to_match_payload(citizen_id, history_id) for recommendation in recommendations]
        return self.repo.match_repo.create_many(payloads)

    def add_logs(self, citizen_id: str, history_id: str, log_rows: list[dict[str, Any]]) -> list[Any]:
        payloads = []
        for row in log_rows:
            payloads.append({"citizen_id": citizen_id, "history_id": history_id, **row})
        return self.repo.log_repo.create_many(payloads)


class EligibilityEngineService:
    REQUIRED_DOCUMENT_KEYWORDS = [
        "aadhaar",
        "ration card",
        "income certificate",
        "community certificate",
        "residence certificate",
        "land record",
        "disability certificate",
        "farmer id",
        "caste certificate",
        "birth certificate",
    ]

    def __init__(self, db: Session):
        self.db = db
        self.context_service = CitizenContextService(db)
        self.rule_repo = EligibilityRuleRepository(db)
        self.rule_eval = RuleEvaluationService()
        self.similarity_service = SimilarityService()
        self.explanation_service = ExplanationService()
        self.ranking_service = RankingService()
        self.scheme_repo = GovernmentSchemeRepository(db)
        self.scheme_service = GovernmentSchemeService(db)

    def generate_query(self, context: CitizenContext, category: str | None = None, state: str | None = None, query_override: str | None = None) -> str:
        if query_override:
            return query_override.strip()
        return self.similarity_service.build_query(context, category=category, state=state)

    def _active_rules(self, scheme: GovernmentScheme, category: str | None = None, state: str | None = None) -> list[RuleDefinition]:
        self.rule_repo.seed_defaults()
        rules = self.rule_repo.list_active()
        configured = [RuleDefinition.from_rule_model(rule) for rule in rules if self._rule_applies(rule, scheme, category, state)]
        if not configured:
            configured = [RuleDefinition.from_rule_model(rule) for rule in rules]
        return configured

    def _rule_applies(self, rule: EligibilityRule, scheme: GovernmentScheme, category: str | None, state: str | None) -> bool:
        scope_type = (rule.scope_type or "global").lower()
        scope_value = (rule.scope_value or "").lower()
        scheme_category = (scheme.category or "").lower()
        scheme_state = (scheme.state or "").lower()
        if scope_type == "global":
            return True
        if scope_type == "category" and scope_value:
            return scope_value in scheme_category or scope_value in _normalize_text(category)
        if scope_type == "state" and scope_value:
            return scope_value == scheme_state or scope_value == _normalize_text(state)
        if scope_type == "scheme" and scope_value:
            return scope_value in _normalize_text(scheme.scheme_name)
        return True

    def _infer_dynamic_rules(self, candidate: SchemeCandidate) -> list[RuleDefinition]:
        text = " ".join(
            [
                candidate.scheme.scheme_name,
                candidate.scheme.description or "",
                candidate.scheme.eligibility_summary or "",
                candidate.scheme.required_documents or "",
                candidate.scheme.application_process or "",
                candidate.aggregated_text,
            ]
        )
        clauses: list[RuleDefinition] = []

        for amount in re.findall(r"(?:income|benefit|support|limit|threshold)[^\d]{0,40}(\d{2,8})", text, flags=re.IGNORECASE):
            clauses.append(RuleDefinition(code=f"dynamic-income-{candidate.scheme.id}-{amount}", condition="annual_income", operator="<=", value=int(amount), priority=55, description="Income threshold inferred from scheme text", examples=[f"Income <= {amount}"], scope_type="scheme", scope_value=candidate.scheme.scheme_name, is_mandatory=True, source="inferred"))

        if _contains_any(text, ["farmer", "cultivator", "agriculture", "agricultural"]):
            clauses.append(RuleDefinition(code=f"dynamic-farmer-{candidate.scheme.id}", condition="is_farmer", operator="==", value=True, priority=60, description="Farmer requirement inferred from scheme text", examples=["Occupation == Farmer"], scope_type="scheme", scope_value=candidate.scheme.scheme_name, is_mandatory=True, source="inferred"))

        if _contains_any(text, ["senior citizen", "elderly", "old age", "pension"]):
            clauses.append(RuleDefinition(code=f"dynamic-senior-{candidate.scheme.id}", condition="age", operator=">=", value=60, priority=65, description="Senior citizen requirement inferred from scheme text", examples=["Age >= 60"], scope_type="scheme", scope_value=candidate.scheme.scheme_name, is_mandatory=True, source="inferred"))

        if _contains_any(text, ["disabled", "disability", "handicap"]):
            clauses.append(RuleDefinition(code=f"dynamic-disabled-{candidate.scheme.id}", condition="is_disabled", operator="==", value=True, priority=70, description="Disability requirement inferred from scheme text", examples=["Disabled == True"], scope_type="scheme", scope_value=candidate.scheme.scheme_name, is_mandatory=True, source="inferred"))

        if _contains_any(text, ["student", "scholarship", "education", "college"]):
            clauses.append(RuleDefinition(code=f"dynamic-student-{candidate.scheme.id}", condition="student_status", operator="contains", value="student", priority=72, description="Student requirement inferred from scheme text", examples=["Student Status == True"], scope_type="scheme", scope_value=candidate.scheme.scheme_name, is_mandatory=True, source="inferred"))

        if _contains_any(text, ["bpl", "below poverty line", "economically weaker"]):
            clauses.append(RuleDefinition(code=f"dynamic-bpl-{candidate.scheme.id}", condition="is_bpl", operator="==", value=True, priority=75, description="BPL requirement inferred from scheme text", examples=["BPL == True"], scope_type="scheme", scope_value=candidate.scheme.scheme_name, is_mandatory=True, source="inferred"))

        return clauses

    def _extract_required_documents(self, candidate: SchemeCandidate) -> list[str]:
        text = " ".join([candidate.scheme.required_documents or "", candidate.scheme.eligibility_summary or "", candidate.scheme.description or "", candidate.aggregated_text])
        found: list[str] = []
        for keyword in self.REQUIRED_DOCUMENT_KEYWORDS:
            if keyword in text.lower() and keyword not in found:
                found.append(keyword)
        return found

    def _extract_estimated_benefit(self, candidate: SchemeCandidate) -> str | None:
        text = " ".join([candidate.scheme.benefits or "", candidate.scheme.description or "", candidate.aggregated_text])
        amounts = re.findall(r"(?:₹|rs\.?|rupees?)\s*([0-9][0-9,]{2,})", text, flags=re.IGNORECASE)
        if amounts:
            return f"₹{amounts[0].replace(',', '')}"
        amount_words = re.findall(r"(\d+[\d,]*)\s*(?:per\s*month|monthly|annually|annual|year|per\s*year)", text, flags=re.IGNORECASE)
        if amount_words:
            return amount_words[0]
        benefits = (candidate.scheme.benefits or candidate.scheme.description or "").strip()
        return benefits[:200] if benefits else None

    def _profile_match_percentage(self, context: CitizenContext) -> float:
        completeness = context.profile_completion_percentage or 0
        document_bonus = min(20.0, len(context.document_types) * 4.0)
        land_bonus = 10.0 if context.total_land_area > 0 else 0.0
        return round(min(100.0, completeness * 0.7 + document_bonus + land_bonus), 2)

    def _document_score(self, required_documents: list[str], context: CitizenContext) -> float:
        if not required_documents:
            return 100.0 if context.has_documents else 70.0
        matched = 0
        for required in required_documents:
            needle = required.lower()
            if needle in context.document_types or needle in context.document_names:
                matched += 1
        return round((matched / len(required_documents)) * 100.0, 2)

    def _benefit_score(self, candidate: SchemeCandidate) -> float:
        value = self._extract_estimated_benefit(candidate)
        if not value:
            return 40.0
        if re.search(r"\d", value):
            return 85.0
        return 60.0 if len(value) > 20 else 50.0

    def _evaluate_candidate(self, context: CitizenContext, candidate: SchemeCandidate, category: str | None = None, state: str | None = None) -> tuple[SchemeRecommendation, list[dict[str, Any]]]:
        configured_rules = self._active_rules(candidate.scheme, category=category, state=state)
        dynamic_rules = self._infer_dynamic_rules(candidate)
        all_rules = configured_rules + dynamic_rules
        evaluations = self.rule_eval.evaluate_many(context, all_rules)
        matched = [evaluation for evaluation in evaluations if evaluation.passed]
        missing = [evaluation for evaluation in evaluations if not evaluation.passed and evaluation.rule.is_mandatory]
        eligible_rules = [evaluation for evaluation in evaluations if evaluation.rule.is_mandatory]
        passed_rules = [evaluation for evaluation in eligible_rules if evaluation.passed]

        total_rules = len(eligible_rules) if eligible_rules else len(all_rules)
        passed_count = len(passed_rules)
        eligibility_percentage = round((passed_count / total_rules) * 100.0, 2) if total_rules else 100.0
        required_documents = self._extract_required_documents(candidate)
        estimated_benefit = self._extract_estimated_benefit(candidate)
        profile_match_percentage = self._profile_match_percentage(context)
        document_score = self._document_score(required_documents, context)
        benefit_score = self._benefit_score(candidate)
        state_bonus = 5.0 if candidate.scheme.state and _normalize_text(candidate.scheme.state) == _normalize_text(context.state) else (2.5 if candidate.scheme.government_level == "central" else 0.0)
        recency_bonus = self._scheme_recency_bonus(candidate.scheme.updated_at or candidate.scheme.created_at)
        confidence_score = self.ranking_service.confidence(eligibility_percentage, candidate.semantic_score * 100.0, document_score, profile_match_percentage)
        overall_score = self.ranking_service.score(
            eligibility_percentage=eligibility_percentage,
            similarity_score=candidate.semantic_score * 100.0,
            benefit_score=benefit_score,
            profile_match_percentage=profile_match_percentage,
            document_score=document_score,
            state_bonus=state_bonus,
            recency_bonus=recency_bonus,
        )
        application_ready = bool(not missing and document_score >= 50.0 and profile_match_percentage >= 40.0)
        recommendation_reason = self.explanation_service.build(context, evaluations, candidate, required_documents, estimated_benefit)
        matching = SchemeRecommendation(
            scheme=candidate.scheme,
            eligibility_status="eligible" if not missing else "ineligible",
            eligibility_percentage=eligibility_percentage,
            similarity_score=round(candidate.semantic_score * 100.0, 2),
            confidence_score=confidence_score,
            overall_score=overall_score,
            ranking_position=0,
            recommendation_reason=recommendation_reason,
            matched_rules=[self._serialize_evaluation(item) for item in matched],
            missing_requirements=[self._serialize_evaluation(item) for item in missing],
            required_documents=required_documents,
            estimated_benefit=estimated_benefit,
            application_ready=application_ready,
            profile_match_percentage=profile_match_percentage,
            semantic_query=candidate.aggregated_text,
            candidate_chunks=candidate.chunks,
        )
        log_rows = [
            {
                "scheme_id": candidate.scheme.id,
                "rule_id": None,
                "rule_code": evaluation.rule.code,
                "condition": evaluation.rule.condition,
                "operator": evaluation.rule.operator,
                "expected_value": evaluation.expected_value,
                "actual_value": evaluation.actual_value,
                "passed": evaluation.passed,
                "severity": evaluation.severity,
                "details": evaluation.details,
            }
            for evaluation in evaluations
        ]
        return matching, log_rows

    def _serialize_evaluation(self, evaluation: RuleEvaluation) -> dict[str, Any]:
        return {
            "rule_code": evaluation.rule.code,
            "condition": evaluation.rule.condition,
            "operator": evaluation.rule.operator,
            "expected_value": evaluation.expected_value,
            "actual_value": evaluation.actual_value,
            "passed": evaluation.passed,
            "priority": evaluation.rule.priority,
            "description": evaluation.rule.description,
            "source": evaluation.rule.source,
        }

    def _scheme_recency_bonus(self, timestamp: Any) -> float:
        if not timestamp:
            return 0.0
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except ValueError:
                return 0.0
        delta_days = max(0, (datetime.utcnow() - timestamp).days)
        if delta_days <= 30:
            return 5.0
        if delta_days <= 180:
            return 2.5
        return 0.0

    def _group_search_results(self, search_results: list[dict[str, Any]], schemes_by_id: dict[str, GovernmentScheme]) -> list[SchemeCandidate]:
        grouped: dict[str, dict[str, Any]] = {}
        for item in search_results:
            scheme_id = item.get("scheme_id")
            if not scheme_id or scheme_id not in schemes_by_id:
                continue
            grouped.setdefault(scheme_id, {"semantic_score": 0.0, "chunks": []})
            grouped[scheme_id]["semantic_score"] = max(grouped[scheme_id]["semantic_score"], float(item.get("similarity_score", 0.0) or 0.0))
            grouped[scheme_id]["chunks"].append(item)

        candidates: list[SchemeCandidate] = []
        for scheme_id, payload in grouped.items():
            scheme = schemes_by_id[scheme_id]
            ordered_chunks = sorted(payload["chunks"], key=lambda row: float(row.get("similarity_score", 0.0) or 0.0), reverse=True)
            candidates.append(
                SchemeCandidate(
                    scheme=scheme,
                    semantic_score=float(payload["semantic_score"]),
                    chunks=ordered_chunks,
                    aggregated_text=" ".join(chunk.get("matched_content") or chunk.get("relevant_content") or "" for chunk in ordered_chunks[:5]),
                )
            )
        return candidates

    def _fallback_candidates(self, category: str | None = None, state: str | None = None, limit: int = 20) -> list[SchemeCandidate]:
        schemes, _ = self.scheme_service.list_schemes(skip=0, limit=limit, category=category, status="active")
        candidates = []
        for scheme in schemes:
            if state and scheme.state and _normalize_text(scheme.state) != _normalize_text(state):
                continue
            candidates.append(SchemeCandidate(scheme=scheme, semantic_score=0.35, chunks=[], aggregated_text=""))
        return candidates

    def generate(self, citizen_id: str, limit: int = 5, category: str | None = None, state: str | None = None, query_override: str | None = None, request_type: str = "generate") -> tuple[RecommendationHistory, list[SchemeRecommendation], list[dict[str, Any]], CitizenContext, str, int]:
        start_time = time.perf_counter()
        context = self.context_service.build(citizen_id)
        query = self.generate_query(context, category=category, state=state, query_override=query_override)
        self.rule_repo.seed_defaults()

        try:
            search_results = self.scheme_service.semantic_search(query, limit=max(limit, settings.RECOMMENDATION_CANDIDATE_LIMIT), category=category)
        except Exception as exc:
            logger.warning("Semantic search unavailable, using fallback schemes: %s", exc)
            search_results = []

        schemes_by_id: dict[str, GovernmentScheme] = {}
        if search_results:
            for item in search_results:
                scheme_id = item.get("scheme_id")
                if not scheme_id or scheme_id in schemes_by_id:
                    continue
                scheme = self.scheme_repo.get(scheme_id)
                if scheme:
                    item["scheme_object"] = scheme
                    schemes_by_id[scheme_id] = scheme
        if not schemes_by_id:
            fallback_candidates = self._fallback_candidates(category=category, state=state, limit=settings.RECOMMENDATION_CANDIDATE_LIMIT)
            search_results = []
            candidates = fallback_candidates
        else:
            candidates = self._group_search_results(search_results, schemes_by_id)

        recommendations: list[SchemeRecommendation] = []
        log_rows: list[dict[str, Any]] = []
        for candidate in candidates:
            recommendation, logs = self._evaluate_candidate(context, candidate, category=category, state=state)
            log_rows.extend(logs)
            if recommendation.eligibility_status == "eligible":
                recommendations.append(recommendation)

        recommendations.sort(key=lambda item: item.overall_score, reverse=True)
        recommendations = recommendations[:limit]
        for position, recommendation in enumerate(recommendations, start=1):
            recommendation.ranking_position = position

        eligible_count = len(recommendations)
        execution_time_ms = int((time.perf_counter() - start_time) * 1000)
        overall_confidence = round(sum(item.confidence_score for item in recommendations) / eligible_count, 2) if eligible_count else 0.0

        history = RecommendationHistoryRepository(self.db).create(
            {
                "citizen_id": citizen_id,
                "request_type": request_type,
                "query_text": query,
                "top_k": limit,
                "total_candidates": len(candidates),
                "eligible_count": eligible_count,
                "overall_confidence": overall_confidence,
                "status": "completed",
                "execution_time_ms": execution_time_ms,
                "context_snapshot": context.to_snapshot(),
                "notes": None,
                "completed_at": datetime.utcnow(),
            }
        )

        if recommendations:
            RecommendationMatchRepository(self.db).create_many([item.to_match_payload(citizen_id, history.id) for item in recommendations])
        if log_rows:
            self._persist_logs(citizen_id, history.id, log_rows)

        logger.info(
            "Generated recommendations",
            extra={
                "citizen_id": citizen_id,
                "history_id": history.id,
                "eligible_count": eligible_count,
                "candidates": len(candidates),
                "execution_time_ms": execution_time_ms,
            },
        )
        return history, recommendations, log_rows, context, query, execution_time_ms

    def _persist_logs(self, citizen_id: str, history_id: str, log_rows: list[dict[str, Any]]) -> None:
        repository = EligibilityLogRepository(self.db)
        payloads = [{"citizen_id": citizen_id, "history_id": history_id, **row} for row in log_rows]
        repository.create_many(payloads)

    def list_rules(self) -> list[EligibilityRule]:
        return self.rule_repo.seed_defaults()

    def get_latest_recommendations(self, citizen_id: str) -> RecommendationSummaryResponse:
        history = RecommendationHistoryRepository(self.db).get_latest_for_citizen(citizen_id)
        if not history:
            raise RecommendationNotFound()
        matches = RecommendationMatchRepository(self.db).list_for_history(history.id)
        recommendation_items = [self._match_to_response(match) for match in matches]
        return RecommendationSummaryResponse(
            citizen_id=citizen_id,
            generated_at=history.created_at,
            total_candidates=history.total_candidates,
            eligible_count=history.eligible_count,
            top_ranked_scheme=recommendation_items[0].scheme_name if recommendation_items else None,
            overall_confidence=history.overall_confidence,
            recommendations=recommendation_items,
            history=self._history_to_response(history, matches),
        )

    def list_recommendations(self, citizen_id: str) -> RecommendationListResponse:
        matches = RecommendationMatchRepository(self.db).list_for_citizen(citizen_id)
        return RecommendationListResponse(
            citizen_id=citizen_id,
            generated_at=datetime.utcnow(),
            total=len(matches),
            items=[self._match_to_response(match) for match in matches],
        )

    def list_history(self, citizen_id: str, limit: int = 20) -> list[RecommendationHistoryResponse]:
        histories = RecommendationHistoryRepository(self.db).get_for_citizen(citizen_id, limit=limit)
        return [self._history_to_response(history, RecommendationMatchRepository(self.db).list_for_history(history.id)) for history in histories]

    def get_recommendation(self, match_id: str, citizen_id: str) -> RecommendationMatchResponse:
        match = RecommendationMatchRepository(self.db).get(match_id)
        if not match or match.citizen_id != citizen_id:
            raise RecommendationNotFound(match_id)
        return self._match_to_response(match)

    def get_history(self, history_id: str, citizen_id: str) -> RecommendationHistoryResponse:
        history = RecommendationHistoryRepository(self.db).get(history_id)
        if history.citizen_id != citizen_id:
            raise RecommendationNotFound(history_id)
        matches = RecommendationMatchRepository(self.db).list_for_history(history.id)
        return self._history_to_response(history, matches)

    def submit_feedback(self, citizen_id: str, payload: dict[str, Any]) -> RecommendationFeedback:
        history = RecommendationHistoryRepository(self.db).get(payload["history_id"])
        if history.citizen_id != citizen_id:
            raise RecommendationNotFound(payload["history_id"])
        match = RecommendationMatchRepository(self.db).get_by_id if hasattr(RecommendationMatchRepository, "get_by_id") else None
        feedback_repo = RecommendationFeedbackRepository(self.db)
        existing = feedback_repo.get_by_history_and_scheme(citizen_id, payload["history_id"], payload["scheme_id"])
        data = {"citizen_id": citizen_id, **payload}
        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        return feedback_repo.create(data)

    def eligibility_check(self, citizen_id: str, scheme_id: str | None = None, scheme_name: str | None = None, category: str | None = None, state: str | None = None) -> EligibilityCheckResponse:
        context = self.context_service.build(citizen_id)
        if scheme_id:
            scheme = self.scheme_repo.get(scheme_id)
            if not scheme:
                raise RecommendationNotFound(scheme_id)
            candidate = SchemeCandidate(scheme=scheme, semantic_score=0.5, chunks=[], aggregated_text="")
        else:
            query = scheme_name or category or state or context.to_query_text()
            search_results = self.scheme_service.semantic_search(query, limit=1, category=category)
            if not search_results:
                raise RecommendationGenerationError("No eligible schemes matched the current citizen profile")
            candidate = self._candidate_from_search_result(search_results[0])
        recommendation, _ = self._evaluate_candidate(context, candidate, category=category, state=state)
        total_rules = len(recommendation.matched_rules) + len(recommendation.missing_requirements)
        passed_rules = len(recommendation.matched_rules)
        return EligibilityCheckResponse(
            citizen_id=citizen_id,
            evaluated_at=datetime.utcnow(),
            total_rules=total_rules,
            passed_rules=passed_rules,
            eligibility_percentage=recommendation.eligibility_percentage,
            eligible=recommendation.eligibility_status == "eligible",
            matched_rules=recommendation.matched_rules,
            missing_requirements=recommendation.missing_requirements,
            required_documents=recommendation.required_documents,
            application_ready=recommendation.application_ready,
            reasoning=recommendation.recommendation_reason,
        )

    def preview(self, citizen_id: str, limit: int = 5, category: str | None = None, state: str | None = None, query_override: str | None = None) -> EligibilityPreviewResponse:
        history, recommendations, _, _, query, _ = self.generate(citizen_id=citizen_id, limit=limit, category=category, state=state, query_override=query_override, request_type="preview")
        return EligibilityPreviewResponse(
            citizen_id=citizen_id,
            generated_at=history.created_at,
            query=query,
            total_candidates=history.total_candidates,
            eligible_count=history.eligible_count,
            items=[self._match_to_response_match(item, history.id) for item in RecommendationMatchRepository(self.db).list_for_history(history.id)],
        )

    def _candidate_from_search_result(self, search_result: dict[str, Any]) -> SchemeCandidate:
        scheme_id = search_result.get("scheme_id")
        scheme = self.scheme_repo.get(scheme_id) if scheme_id else None
        if not scheme:
            raise RecommendationNotFound(scheme_id or "")
        return SchemeCandidate(scheme=scheme, semantic_score=float(search_result.get("similarity_score", 0.0) or 0.0), chunks=[search_result], aggregated_text=search_result.get("matched_content") or search_result.get("relevant_content") or "")

    def _match_to_response(self, match: CitizenSchemeMatch) -> RecommendationMatchResponse:
        return RecommendationMatchResponse.model_validate(match)

    def _match_to_response_match(self, match: CitizenSchemeMatch, history_id: str) -> RecommendationMatchResponse:
        if match.history_id != history_id:
            raise RecommendationNotFound(match.id)
        return self._match_to_response(match)

    def _history_to_response(self, history: RecommendationHistory, matches: list[CitizenSchemeMatch]) -> RecommendationHistoryResponse:
        response = RecommendationHistoryResponse.model_validate(history)
        response.matches = [self._match_to_response(match) for match in matches]
        return response


class RecommendationService(EligibilityEngineService):
    """Public orchestration service for Module 4 APIs."""

    pass


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return " ".join(_normalize_text(item) for item in value)
    return re.sub(r"\s+", " ", str(value).strip().lower())


def _coerce_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = _normalize_text(value)
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if match:
        try:
            return float(match.group(0))
        except ValueError:
            return None
    return None


def _coerce_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = _normalize_text(value)
    if text in {"true", "1", "yes", "y", "eligible", "farmer", "senior", "disabled"}:
        return True
    if text in {"false", "0", "no", "n", "none", "unknown", "not eligible"}:
        return False
    return None


def _contains_any(text: str, needles: Iterable[str]) -> bool:
    normalized = _normalize_text(text)
    return any(needle.lower() in normalized for needle in needles)