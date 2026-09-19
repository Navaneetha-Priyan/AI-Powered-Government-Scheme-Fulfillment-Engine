"""Module 4 eligibility, semantic search, ranking, and recommendation services."""
from __future__ import annotations

import math
import re
import time
from copy import deepcopy
from collections import defaultdict
from collections.abc import Mapping
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
from app.models.scheme_rules import get_scheme_eligibility_for_scheme
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
from app.services.eligibility_catalog_service import get_catalogue_entry_for_scheme
from app.services.eligibility_evaluator import EligibilityEvaluator, get_eligibility_evaluator
from app.services.government_scheme_service import GovernmentSchemeService
from app.services.scheme_presentation_service import presentation_for_scheme

logger = get_logger(__name__)

# ── Canonical eligibility-status vocabulary ─────────────────────────────────
# Two vocabularies coexist in the codebase:
#   - Fallback rule-based path: "eligible" | "possibly_eligible" | "not_eligible"
#   - Structured path (EligibilityStatus): "eligible" | "potentially_eligible" |
#     "insufficient_information" | "not_eligible"
# They mean the same thing and MUST be filtered and ranked consistently.
# Filtering only on the fallback vocabulary silently drops every
# structured-evaluated scheme that is not fully "eligible" (e.g. schemes whose
# evaluation is pending missing citizen information), which removes correct
# rank-1 candidates from the final recommendations.
ELIGIBILITY_STATUS_RANK_BOOST: dict[str, float] = {
    "eligible": 1000.0,
    "possibly_eligible": 750.0,         # fallback vocabulary: mandatory rules with unknowns
    "potentially_eligible": 500.0,      # structured vocabulary
    "insufficient_information": 100.0,  # structured: mandatory info missing, nothing failed
    "not_eligible": 0.0,
    "ineligible": 0.0,                  # legacy alias
}
# Statuses that may appear in recommendations (anything not ruled out).
RECOMMENDABLE_ELIGIBILITY_STATUSES = frozenset(
    status for status, boost in ELIGIBILITY_STATUS_RANK_BOOST.items() if boost > 0
)

# Bonus applied when the user's query explicitly names the scheme. This prevents
# an unrelated adjacent scheme from outranking an eligible exact/strongly
# matching scheme purely on a marginally higher generic similarity score.
# The bonus is smaller than every status-tier gap, so it never reorders schemes
# across eligibility statuses (eligible > possibly/potentially > insufficient).
STRONG_NAME_MATCH_BONUS: float = 150.0
_NAME_GENERIC_TOKENS = {
    "scheme", "schemes", "guidelines", "document", "documents", "operational",
    "yojana", "and", "the", "for", "mission", "2", "3",
}


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
    # Canonical citizen evidence view (built by CitizenContextService via
    # CitizenEvidenceService). Present on all contexts built through the
    # service; adapted from raw sets for hand-constructed/test contexts.
    citizen_evidence: Any = None
    verified_document_types: set[str] = field(default_factory=set)

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
        from app.services.citizen_evidence_service import citizen_evidence_for as _evidence_for  # local import: avoid cycle

        try:
            evidence_view = _evidence_for(self)
            evidence_states = dict(evidence_view.states)
            unmapped = list(evidence_view.unmapped_types)
        except Exception:  # pragma: no cover - snapshot must never fail
            evidence_states = {}
            unmapped = []
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
            "document_names": sorted(self.document_names),
            "verified_document_types": sorted(self.verified_document_types),
            "evidence_states": evidence_states,
            "unmapped_document_types": unmapped,
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
    # Canonical evidence requirements the authoritative evaluation found
    # unsatisfied (e.g. ``["bank_account"]``). This is EVIDENCE, not rules: it
    # is deliberately kept separate from ``missing_requirements`` (which holds
    # FAIL/UNKNOWN eligibility conditions). Recomputed on every evaluation and
    # never persisted, so it can never become a stale snapshot.
    missing_evidence: list[str] = field(default_factory=list)

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
        profile_completion = int(getattr(profile, "profile_completion_percentage", 0) or 0)

        # Canonical evidence: government (DigiLocker) documents and the Build
        # My Profile ``uploaded_documents`` resolve through the same alias map
        # (``citizen_evidence_service``), so uploaded+verified Aadhaar/Land
        # Record is visible to eligibility as ``aadhaar``/``land_record``.
        # ``context_service`` now owns the merge; eligibility only reads the
        # canonical ``citizen_evidence`` view (with raw sets adapted only for
        # persisted-snapshot/test compatibility).
        from app.services.citizen_evidence_service import CitizenEvidenceService

        evidence = CitizenEvidenceService(self.db).build(citizen_id)
        document_types = set(evidence.available_types)
        document_names = set(evidence.names)
        verified_types = set(evidence.verified_types)

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
            citizen_evidence=evidence,
            verified_document_types=verified_types,
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


def _missing_key(entry: Any) -> str:
    """Best-effort raw evidence key for one missing_requirements entry."""
    if entry is None:
        return ""
    if isinstance(entry, str):
        return _normalize_text(entry).replace(" ", "_")
    if isinstance(entry, Mapping):
        for field in ("field", "condition", "rule_code", "code", "description"):
            value = entry.get(field)
            if value:
                return _normalize_text(value).replace(" ", "_")
        return ""
    for attr in ("field", "condition", "rule_code", "code", "description"):
        value = getattr(entry, attr, None)
        if value:
            return _normalize_text(value).replace(" ", "_")
    return ""


def _condition_counts(matched_rules: Any, missing_requirements: Any) -> tuple[int, int]:
    """Count citizen-presentable mandatory conditions from serialized rules.

    Works on the serialized condition dicts embedded in recommendations and
    eligibility-check payloads (``_serialize_structured_condition`` output for
    the structured engine, ``_serialize_evaluation`` output for the legacy
    rule engine). Returns ``(passed, total)`` where:

    - optional conditions (``mandatory == False`` / ``severity == optional``)
      are excluded — citizens are never blocked by preference rules;
    - ``NOT_APPLICABLE`` conditions (conditional rules that did not apply)
      are excluded;
    - ``PASS`` counts as met, ``FAIL``/``UNKNOWN`` count as not met;
    - legacy payloads without a ``result`` key fall back to ``passed``.
    """
    total = 0
    passed = 0
    for item in list(matched_rules or []) + list(missing_requirements or []):
        if not isinstance(item, Mapping):
            continue
        if item.get("mandatory") is False or item.get("severity") == "optional":
            continue
        result = str(item.get("result") or "").strip().upper()
        if result in {"NOT_APPLICABLE", "MANUAL_REVIEW"}:
            continue
        total += 1
        if result == "PASS" or (not result and item.get("passed") is True):
            passed += 1
    return passed, total


def _missing_evidence_for(
    context: "CitizenContext",
    required_documents: Iterable[str] | None,
) -> list[str]:
    """Authoritative evidence shortfall for one requirement set.

    Uses the SAME canonical citizen evidence view the evaluator uses
    (``citizen_evidence_service``), so a document the citizen has uploaded and
    verified can never be reported as missing. Requirement keys the alias table
    does not positively recognise are reported as missing rather than being
    silently satisfied.
    """
    required = [str(item or "").strip().lower() for item in (required_documents or [])]
    required = [item for item in required if item]
    if not required:
        return []

    evidence = getattr(context, "citizen_evidence", None)
    if evidence is None:
        try:
            from app.services.citizen_evidence_service import evidence_from_raw_types

            evidence = evidence_from_raw_types(
                getattr(context, "document_types", None) or [],
                getattr(context, "document_names", None) or [],
                verified_types=getattr(context, "verified_document_types", None),
            )
        except Exception:  # pragma: no cover - defensive
            evidence = None

    if evidence is None:
        return list(required)

    try:
        return list(evidence.missing_requirements(required))
    except Exception:  # pragma: no cover - defensive
        return list(required)


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


def _has_retrieval_artifacts(text: str) -> bool:
    """True when text still carries RAG/OCR pipeline bookkeeping.

    Fragments such as ``SMAM Operational Guidelines 2025 smam-guidelines.pdf
    chunk`` are pipeline output, not scheme prose, and must never become the
    citizen-facing description even when nothing better exists for a scheme.
    """
    normalized = _normalize_text(text)
    if not normalized:
        return True
    if ".pdf" in normalized or ".docx" in normalized:
        return True
    return any(
        marker in normalized
        for marker in (
            "chunk",
            "retrieved",
            "embedding",
            "similarity score",
            "page no",
            "page number",
            "ocr",
        )
    )


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
        self.eligibility_evaluator = get_eligibility_evaluator()

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

    def _public_scheme_description(self, scheme: GovernmentScheme) -> str | None:
        """Return citizen-facing scheme text from stored scheme metadata.

        Recommendation detail should not use retrieval chunks as the scheme
        overview. Prefer existing curated fields; when the scheme has no clean
        metadata, lightly cleaned source text is preserved — but obviously
        unrelated fragments (letterhead addresses, page headers, OCR artifacts)
        are never presented as the scheme description.
        """
        candidates = (
            getattr(scheme, "description", None),
            getattr(scheme, "eligibility_summary", None),
            getattr(scheme, "benefits", None),
        )
        for value in candidates:
            clean = self._clean_public_scheme_text(value, max_length=500)
            if (
                clean
                and not self._looks_like_raw_source_dump(clean, scheme)
                and not self._looks_like_unrelated_fragment(clean)
            ):
                return clean
        # No curated metadata: preserve the cleaned source text, but still
        # refuse addresses / letterheads / OCR headers / retrieval artifacts.
        for value in candidates:
            clean = self._clean_public_scheme_text(value, max_length=320)
            if (
                clean
                and not self._looks_like_unrelated_fragment(clean)
                and not _has_retrieval_artifacts(clean)
            ):
                return clean
        return None

    def _public_scheme_benefits(self, scheme: GovernmentScheme) -> str | None:
        for value in (getattr(scheme, "benefits", None), getattr(scheme, "description", None)):
            clean = self._clean_public_scheme_text(value, max_length=300)
            if (
                clean
                and not self._looks_like_raw_source_dump(clean, scheme)
                and not self._looks_like_unrelated_fragment(clean)
            ):
                return clean
        return None

    @staticmethod
    def _clean_public_scheme_text(value: Any, *, max_length: int) -> str | None:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        if not text:
            return None
        # Page number / leading list numbering.
        text = re.sub(r"^(?:page\s*(?:no\.?)?\s*\d+|[0-9]+\s+)", "", text, flags=re.IGNORECASE).strip()
        # Letterhead heading run ("PRADHAN MANTRI KISAN SAMMAN NIDHI SCHEME ...").
        text = re.sub(r"^[\d\s.,;:\-]*[A-Z][A-Z0-9\s()/&.,'\-]{12,}", "", text).strip()
        # Letterhead address fragments ("New Delhi-110001", "NewDelhi 110001").
        text = re.sub(
            r"\bNew\s*Delhi\b\s*[-\u2013]?\s*(?:pin\s*(?:code)?\s*[-\u2013:]?\s*)?\d{0,6}",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()
        text = re.sub(r"\bNewDelhi\b\s*[-\u2013]?\s*\d{0,6}", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(
            r"\b(?:pin\s*(?:code)?|pincode)\s*[-\u2013:]?\s*\d{6}\b",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()
        text = re.sub(r"\bDated\s*:?\s*[^.]{0,40}", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"\bF\.?\s*No\.?\s*[:\-\w/(). ]{3,80}", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"\s+", " ", text).strip(" ,.;:-")
        if not text:
            return None
        if len(text) <= max_length:
            return text
        truncated = text[:max_length]
        boundary = truncated.rfind(" ")
        if boundary > max_length * 0.6:
            truncated = truncated[:boundary]
        return truncated.rstrip(" ,.;:-") + "..."

    # Letterhead / OCR artifacts that must never become citizen-facing text.
    _LETTERHEAD_TOKENS = (
        "newdelhi",
        "new delhi",
        "krishi bhawan",
        "kisan bhawan",
        "udyog bhawan",
        "shastri bhawan",
        "niti ayog",
        "www.",
        "http",
        "@gov.in",
        "@nic.in",
        "e-mail",
        "telefax",
        "telephone",
        "fax",
        "pin code",
        "pincode",
        "f.no",
        "f. no",
    )

    @classmethod
    def _looks_like_unrelated_fragment(cls, text: str) -> bool:
        """True for letterhead addresses / page headers / OCR artifacts.

        A real sentence that merely mentions an address is preserved; only
        fragments whose letterhead content dominates (or that are nothing but a
        pincode/address) are rejected. This keeps "preserve the source text"
        honest without letting a scanned letterhead become the scheme summary.
        """
        normalized = _normalize_text(text)
        if not normalized:
            return True
        stripped = normalized.strip(" ,.;:-")
        if re.fullmatch(r"(?:new\s*delhi[-\s]*)?\d{6}", stripped):
            return True
        hits = sum(1 for token in cls._LETTERHEAD_TOKENS if token in normalized)
        if hits == 0:
            return False
        without_tokens = normalized
        for token in cls._LETTERHEAD_TOKENS:
            without_tokens = without_tokens.replace(token, " ")
        without_tokens = re.sub(r"[\d\W_]+", " ", without_tokens).strip()
        return len(text) <= 120 or len(without_tokens) < 60

    @staticmethod
    def _looks_like_raw_source_dump(text: str, scheme: GovernmentScheme | None = None) -> bool:
        normalized = _normalize_text(text)
        if not normalized:
            return True
        if _has_retrieval_artifacts(text):
            return True
        markers = (
            "page no",
            ".pdf",
            "new delhi",
            "dated:",
            "subject:",
            "directory",
            "lead implementing agency",
            "cooperation & farmers",
            "f.no",
        )
        marker_hits = sum(1 for marker in markers if marker in normalized)
        alpha_chars = [char for char in text if char.isalpha()]
        upper_ratio = sum(1 for char in alpha_chars if char.isupper()) / max(1, len(alpha_chars))
        starts_like_heading = bool(re.match(r"^\d+\s+[A-Z][A-Z\s()/&.-]{20,}", text))
        scheme_name = _normalize_text(getattr(scheme, "scheme_name", "") if scheme else "")
        mostly_title = bool(
            scheme_name
            and normalized.replace("-", " ").startswith(scheme_name.replace("-", " ")[:30])
            and len(text) > 120
        )
        return marker_hits >= 2 or starts_like_heading or (upper_ratio > 0.65 and len(text) > 80) or mostly_title

    def _profile_match_percentage(self, context: CitizenContext) -> float:
        completeness = context.profile_completion_percentage or 0
        document_bonus = min(20.0, len(context.document_types) * 4.0)
        land_bonus = 10.0 if context.total_land_area > 0 else 0.0
        return round(min(100.0, completeness * 0.7 + document_bonus + land_bonus), 2)

    def _document_score(self, required_documents: list[str], context: CitizenContext) -> float:
        if not required_documents:
            return 100.0 if context.has_documents else 70.0
        try:
            from app.services.citizen_evidence_service import evidence_from_raw_types
            evidence = getattr(context, "citizen_evidence", None)
            if evidence is None:
                evidence = evidence_from_raw_types(
                    getattr(context, "document_types", None) or [],
                    getattr(context, "document_names", None) or [],
                    verified_types=getattr(context, "verified_document_types", None),
                )
            matched = sum(1 for required in required_documents if evidence.satisfies(required))
        except Exception:
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
        # The PDF-derived catalogue is the canonical structured rule source.
        # scheme_rules.py remains only as a compatibility layer for schemes not
        # yet mapped into the catalogue.
        catalogue_entry = get_catalogue_entry_for_scheme(candidate.scheme)
        if catalogue_entry is not None:
            return self._evaluate_candidate_structured(context, candidate, catalogue_entry)

        # Try legacy structured eligibility rules next.
        structured_eligibility = get_scheme_eligibility_for_scheme(candidate.scheme)
        
        if structured_eligibility is not None:
            return self._evaluate_candidate_structured(context, candidate, structured_eligibility)
        
        # Fallback to existing rule-based evaluation
        return self._evaluate_candidate_fallback(context, candidate, category, state)

    def _evaluate_candidate_structured(
        self, 
        context: CitizenContext, 
        candidate: SchemeCandidate, 
        structured_eligibility: Any
    ) -> tuple[SchemeRecommendation, list[dict[str, Any]]]:
        """Evaluate using structured eligibility rules from scheme PDFs."""
        from app.models.scheme_eligibility import EligibilityStatus
        
        if hasattr(structured_eligibility, "rules") and hasattr(structured_eligibility, "pdf_filename"):
            eligibility_result = self.eligibility_evaluator.evaluate_catalogue_entry(
                structured_eligibility,
                context,
            )
        else:
            eligibility_result = self.eligibility_evaluator.evaluate(structured_eligibility, context)
        
        # Map structured result to recommendation fields
        eligibility_status = eligibility_result.status
        eligibility_percentage = eligibility_result.eligibility_percentage
        
        required_documents = (
            list(getattr(eligibility_result, "evidence_requirements", []) or [])
            or self._extract_required_documents(candidate)
        )
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
        
        # Determine application readiness based on structured result
        has_missing_mandatory = eligibility_result.has_missing_mandatory()
        has_mandatory_failures = eligibility_result.has_mandatory_failures()
        application_ready = bool(
            eligibility_status == EligibilityStatus.ELIGIBLE 
            and document_score >= 50.0 
            and profile_match_percentage >= 40.0
        )
        
        # Build recommendation reason from structured result
        recommendation_reason = self._build_structured_reason(eligibility_result, candidate, required_documents, estimated_benefit)
        
        # Serialize structured conditions for API response
        matched_rules = [self._serialize_structured_condition(c) for c in eligibility_result.matched_conditions]
        missing_requirements = [self._serialize_structured_condition(c) for c in eligibility_result.failed_conditions + eligibility_result.missing_information]
        
        matching = SchemeRecommendation(
            scheme=candidate.scheme,
            eligibility_status=eligibility_status,
            eligibility_percentage=eligibility_percentage,
            similarity_score=round(candidate.semantic_score * 100.0, 2),
            confidence_score=confidence_score,
            overall_score=overall_score,
            ranking_position=0,
            recommendation_reason=recommendation_reason,
            matched_rules=matched_rules,
            missing_requirements=missing_requirements,
            required_documents=required_documents,
            estimated_benefit=estimated_benefit,
            application_ready=application_ready,
            profile_match_percentage=profile_match_percentage,
            semantic_query=candidate.aggregated_text,
            candidate_chunks=candidate.chunks,
            missing_evidence=list(getattr(eligibility_result, "missing_evidence", []) or []),
        )
        
        # Build log rows for audit trail
        log_rows = self._build_structured_log_rows(candidate.scheme.id, eligibility_result)
        
        return matching, log_rows

    def _evaluate_candidate_fallback(
        self, 
        context: CitizenContext, 
        candidate: SchemeCandidate, 
        category: str | None = None, 
        state: str | None = None
    ) -> tuple[SchemeRecommendation, list[dict[str, Any]]]:
        """Existing rule-based evaluation logic (unchanged)."""
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
        has_unknowns = any(
            not item.passed and item.actual_value in (None, "", [], {}, ())
            for item in evaluations
            if item.rule.is_mandatory
        )
        eligibility_status = "eligible" if not missing else ("possibly_eligible" if has_unknowns else "not_eligible")
        application_ready = bool(not missing and document_score >= 50.0 and profile_match_percentage >= 40.0)
        recommendation_reason = self.explanation_service.build(context, evaluations, candidate, required_documents, estimated_benefit)
        matching = SchemeRecommendation(
            scheme=candidate.scheme,
            eligibility_status=eligibility_status,
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
            missing_evidence=_missing_evidence_for(context, required_documents),
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

    def _serialize_structured_condition(self, condition: Any) -> dict[str, Any]:
        """Serialize an EligibilityConditionResult for API response."""
        return {
            "condition": condition.condition,
            "rule_id": condition.rule_id,
            "field": condition.field,
            "operator": condition.operator,
            "rule_type": condition.rule_type,
            "result": condition.result,
            "passed": condition.passed,
            "actual_value": condition.actual_value,
            "expected_value": condition.expected_value,
            "mandatory": condition.mandatory,
            "notes": condition.notes,
            "source_document": condition.source_document,
            "evidence": [
                {
                    "chunk_id": e.chunk_id,
                    "scheme_id": e.scheme_id,
                    "document_id": e.document_id,
                    "page_number": e.page_number,
                    "section_name": e.section_name,
                    "text": e.text,
                }
                for e in condition.evidence
            ],
        }

    def _build_structured_reason(
        self, 
        eligibility_result: Any, 
        candidate: SchemeCandidate, 
        required_documents: list[str], 
        estimated_benefit: str | None
    ) -> str:
        """Build human-readable recommendation reason from structured eligibility result."""
        matched = [c.condition for c in eligibility_result.matched_conditions if c.mandatory]
        failed = [c.condition for c in eligibility_result.failed_conditions if c.mandatory]
        missing = [c.condition for c in eligibility_result.missing_information if c.mandatory]
        
        fragments = [f"{candidate.scheme.scheme_name}: {eligibility_result.status.replace('_', ' ').title()}"]
        
        if matched:
            fragments.append("Matched: " + ", ".join(matched[:5]))
        if failed:
            fragments.append("Failed: " + ", ".join(failed[:5]))
        if missing:
            fragments.append("Missing info: " + ", ".join(missing[:5]))
        if required_documents:
            fragments.append("Documents: " + ", ".join(required_documents[:5]))
        if estimated_benefit:
            fragments.append(f"Benefit: {estimated_benefit}")
        fragments.append(f"Similarity Score {round(candidate.semantic_score * 100, 1)}%")
        
        return " | ".join(fragments)

    def _build_structured_log_rows(self, scheme_id: str, eligibility_result: Any) -> list[dict[str, Any]]:
        """Build audit log rows from structured eligibility result."""
        log_rows = []
        
        all_conditions = (
            eligibility_result.matched_conditions 
            + eligibility_result.failed_conditions 
            + eligibility_result.missing_information
        )
        
        for condition in all_conditions:
            log_rows.append({
                "scheme_id": scheme_id,
                "rule_id": None,
                "rule_code": condition.rule_id or f"structured-{condition.condition}",
                "condition": condition.condition,
                "operator": condition.operator or "structured",
                "expected_value": condition.expected_value,
                "actual_value": condition.actual_value,
                "passed": condition.passed,
                "severity": "high" if condition.mandatory and not condition.passed else "info",
                "details": {
                    "mandatory": condition.mandatory,
                    "missing": condition in eligibility_result.missing_information,
                    "result": condition.result,
                    "rule_type": condition.rule_type,
                    "source_document": condition.source_document,
                    "evidence_count": len(condition.evidence),
                },
            })
        
        return log_rows

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
        farmer_discovery_query = (
            request_type == "voice"
            and not any(self._strong_name_match(query, candidate.scheme.scheme_name) for candidate in candidates)
            and any(
                token in _normalize_text(query).lower().split()
                for token in ("farmer", "farmers", "agriculture", "agricultural", "cultivator")
            )
        )
        for candidate in candidates:
            recommendation, logs = self._evaluate_candidate(context, candidate, category=category, state=state)
            log_rows.extend(logs)
            if (
                recommendation.eligibility_status in RECOMMENDABLE_ELIGIBILITY_STATUSES
                or farmer_discovery_query
            ):
                recommendations.append(recommendation)

        # Sort by overall_score, but apply eligibility status as a tiebreaker/boost.
        # Additionally, when the user's query explicitly names a scheme, that
        # scheme receives a bonus so an unrelated adjacent scheme cannot outrank
        # it on a marginally higher generic similarity score. The bonus is smaller
        # than any status-tier gap, so eligibility status still dominates.
        def _rank_key(item: SchemeRecommendation):
            status_boost = self._eligibility_rank_boost(item.eligibility_status)
            if self._strong_name_match(query, item.scheme.scheme_name):
                status_boost += STRONG_NAME_MATCH_BONUS
            return (status_boost, item.overall_score)

        recommendations.sort(key=_rank_key, reverse=True)
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

    def _strong_name_match(self, query_text: str, scheme_name: str) -> bool:
        """True when the user's query explicitly names this scheme.

        Compares distinctive tokens of the catalog scheme name against the
        query text (generic words like "scheme"/"guidelines" are ignored).
        For names with 1-2 distinctive tokens all must appear; longer names
        allow one token to be missing (e.g. version suffixes).
        """
        query_norm = _normalize_text(query_text or "").lower()
        name_norm = _normalize_text(scheme_name or "").lower()
        if not query_norm or not name_norm:
            return False
        tokens = [t for t in re.split(r"\s+", name_norm) if len(t) > 1 and t not in _NAME_GENERIC_TOKENS]
        if not tokens:
            return False
        required = len(tokens) if len(tokens) <= 2 else len(tokens) - 1
        hits = sum(1 for token in tokens if token in query_norm)
        return hits >= required

    def _eligibility_rank_boost(self, eligibility_status: str) -> float:
        """Return a ranking boost factor based on eligibility status.

        This ensures eligible schemes rank higher than potentially_eligible,
        which rank higher than insufficient_information, when overall_score is similar.
        Uses the canonical vocabulary map so the fallback path ("possibly_eligible")
        and the structured path are ranked consistently.
        """
        return ELIGIBILITY_STATUS_RANK_BOOST.get(eligibility_status, 0.0)

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
        mandatory_passed, mandatory_total = _condition_counts(
            recommendation.matched_rules, recommendation.missing_requirements
        )
        return EligibilityCheckResponse(
            citizen_id=citizen_id,
            evaluated_at=datetime.utcnow(),
            total_rules=total_rules,
            passed_rules=passed_rules,
            eligibility_percentage=recommendation.eligibility_percentage,
            eligible=recommendation.eligibility_status == "eligible",
            eligibility_status=recommendation.eligibility_status,
            matched_rules=recommendation.matched_rules,
            missing_requirements=recommendation.missing_requirements,
            required_documents=recommendation.required_documents,
            application_ready=recommendation.application_ready,
            reasoning=recommendation.recommendation_reason,
            mandatory_rules_total=mandatory_total,
            mandatory_rules_passed=mandatory_passed,
            evidence_checklist=self._build_evidence_checklist(
                citizen_id,
                recommendation.required_documents,
                recommendation.missing_requirements,
                recommendation.missing_evidence,
            ),
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
        response = RecommendationMatchResponse.model_validate(match)
        current = self._current_recommendation_for_match(match)
        if current is not None:
            self._apply_current_recommendation(response, current)
        else:
            response.evidence_checklist = self._evidence_checklist_for_match(match)
        # Structured citizen presentation (curated, PDF-grounded). Additive:
        # the legacy sanitized description/benefits strings above are untouched.
        self._apply_presentation(response, match.scheme_id)
        return response

    def _apply_presentation(
        self, response: RecommendationMatchResponse, scheme_id: str
    ) -> None:
        """Populate display_name / short_description / benefits_list.

        Content comes from the curated presentation metadata; raw PDF
        extraction is never placed in these fields.
        """
        try:
            scheme = self.scheme_repo.get(scheme_id)
            presentation = presentation_for_scheme(scheme)
        except Exception as exc:  # pragma: no cover - presentation is non-critical
            logger.warning("Presentation metadata unavailable for %s: %s", scheme_id, exc)
            return
        response.display_name = presentation["display_name"]
        response.short_description = presentation["short_description"]
        response.benefits_list = presentation["benefits"]

    def _current_recommendation_for_match(
        self, match: CitizenSchemeMatch
    ) -> SchemeRecommendation | None:
        scheme = self.scheme_repo.get(match.scheme_id)
        if scheme is None:
            return None
        try:
            context = self.context_service.build(match.citizen_id)
            candidate = SchemeCandidate(
                scheme=scheme,
                semantic_score=float((match.similarity_score or 0.0) / 100.0),
                chunks=[],
                aggregated_text="",
            )
            recommendation, _ = self._evaluate_candidate(context, candidate)
            recommendation.ranking_position = match.ranking_position
            return recommendation
        except Exception as exc:  # pragma: no cover - stale snapshot fallback
            logger.warning(
                "Could not refresh recommendation match %s from current context: %s",
                match.id,
                exc,
            )
            return None

    def _apply_current_recommendation(
        self,
        response: RecommendationMatchResponse,
        current: SchemeRecommendation,
    ) -> None:
        mandatory_passed, mandatory_total = _condition_counts(
            current.matched_rules,
            current.missing_requirements,
        )
        response.scheme_name = current.scheme.scheme_name
        response.description = self._public_scheme_description(current.scheme)
        response.benefits = self._public_scheme_benefits(current.scheme)
        response.eligibility_status = str(
            getattr(current.eligibility_status, "value", current.eligibility_status)
        )
        response.eligibility_percentage = current.eligibility_percentage
        response.confidence_score = current.confidence_score
        response.overall_score = current.overall_score
        response.recommendation_reason = current.recommendation_reason
        response.matched_rules = deepcopy(current.matched_rules)
        response.missing_requirements = deepcopy(current.missing_requirements)
        response.required_documents = list(current.required_documents)
        response.estimated_benefit = current.estimated_benefit
        response.application_ready = current.application_ready
        response.profile_match_percentage = current.profile_match_percentage
        response.semantic_query = ""
        response.mandatory_rules_total = mandatory_total
        response.mandatory_rules_passed = mandatory_passed
        response.evidence_checklist = self._build_evidence_checklist(
            response.citizen_id,
            current.required_documents,
            current.missing_requirements,
            current.missing_evidence,
        )

    def _match_to_response_match(self, match: CitizenSchemeMatch, history_id: str) -> RecommendationMatchResponse:
        if match.history_id != history_id:
            raise RecommendationNotFound(match.id)
        return self._match_to_response(match)

    def _evidence_checklist_for_match(
        self, match: CitizenSchemeMatch
    ) -> list[dict[str, Any]]:
        """Serialize the centralized evidence checklist for one match.

        Uses the match's own required_documents plus the citizen's CURRENT
        uploaded/verified documents, and recomputes the evidence shortfall live
        from the canonical evidence layer (not from a stale snapshot), so
        "Still needed" flips to "available" as soon as the user uploads.
        Engine requirements are never hidden or weakened here.
        """
        missing_evidence: list[str] = []
        try:
            context = self.context_service.build(match.citizen_id)
            missing_evidence = _missing_evidence_for(
                context, match.required_documents or []
            )
        except Exception:  # pragma: no cover - defensive
            missing_evidence = []
        return self._build_evidence_checklist(
            match.citizen_id,
            match.required_documents or [],
            match.missing_requirements or [],
            missing_evidence,
        )

    def _build_evidence_checklist(
        self,
        citizen_id: str,
        required: Iterable[Any],
        missing_entries: Iterable[Any],
        missing_evidence: Iterable[Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Build the citizen evidence checklist from raw requirement keys.

        Shared by the stored-match serializer and the live
        ``/eligibility/check`` endpoint so both expose identical
        human-readable labels and document status. Uses the existing
        ``resolve_evidence_checklist`` mapping — no second mapping table.

        ``missing_entries`` carries the FAILED/UNKNOWN eligibility conditions
        (rule outcomes); ``missing_evidence`` carries the canonical evidence
        requirements the evaluator found unsatisfied. Both are needed and both
        are kept distinct: the former drives the "information needed" prompts
        for profile facts, the latter marks a genuinely absent document as
        ``needed`` instead of ``manual``. A verified document can never appear
        in either set because both are resolved against the citizen's CURRENT
        canonical evidence.
        """
        from app.services.evidence_mapping_service import (
            resolve_evidence_checklist,
        )

        required_keys = [str(d or "") for d in (required or [])]
        missing_keys = {_missing_key(entry) for entry in (missing_entries or [])}
        missing_keys.update(
            str(entry or "").strip().lower() for entry in (missing_evidence or [])
        )
        missing_keys.discard("")
        try:
            built = self.context_service.build(citizen_id)
            evidence = getattr(built, "citizen_evidence", None)
            if evidence is not None:
                verified_types: set[str] = set(getattr(evidence, "verified_types", set()) or set())
            else:
                verified_types = set(getattr(built, "verified_document_types", set()) or set())
            uploaded: set[str] = set(getattr(built, "document_types", set()) or set())
        except Exception:
            uploaded = set()
            verified_types = set()
        checklist = resolve_evidence_checklist(
            required_keys,
            uploaded,
            missing_only=sorted(missing_keys),
            verified_document_types=verified_types,
        )
        return [item.to_dict() for item in checklist]

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
