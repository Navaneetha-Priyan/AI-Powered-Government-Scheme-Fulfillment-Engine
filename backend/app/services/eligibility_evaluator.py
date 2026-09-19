
"""Structured eligibility evaluator for government schemes.

This service evaluates a :class:`SchemeEligibility` (structured rules extracted
from official scheme PDFs) against a citizen's verified profile and land
records, producing an :class:`EligibilityResult`.

Design rules
------------
- Reuses the existing :class:`CitizenContext` (from ``recommendation_service``)
  as the citizen data source, so no new citizen aggregation is introduced.
- Uses ONLY information actually available in ``CitizenProfile``, ``Citizen``,
  and ``LandRecord``. It never invents missing citizen information.
- Distinguishes a condition that FAILED (data present, requirement not met)
  from a condition that CANNOT BE EVALUATED (data absent) — the latter is
  reported as missing information, not as a failure.
- Uses "any land record satisfies" semantics: a citizen may hold multiple land
  records, and a scheme land requirement is satisfied if ANY appropriate
  record meets it.
- Treats social-category / priority groups (SC/ST/women/small farmer, etc.) as
  PREFERENCES, not mandatory eligibility requirements, unless the scheme rule
  explicitly marks them mandatory. A citizen not in a priority group is NOT
  made ineligible by that alone.
- Preserves evidence traceability from the structured scheme rules.
"""
from __future__ import annotations

from typing import Any, Iterable, List, Optional, TYPE_CHECKING

from app.models.government_scheme import GovernmentScheme
from app.models.scheme_eligibility import (
    EligibilityConditionResult,
    EligibilityResult,
    EligibilityStatus,
    EvidenceSource,
    SchemeEligibility,
    SchemeEligibilityCatalogueEntry,
    StructuredEligibilityRule,
    CriterionState,
    determine_status,
    normalize_eligibility_status,
)
from app.models.scheme_rules import get_scheme_eligibility_for_scheme
from app.services.citizen_evidence_service import (
    CitizenEvidence,
    EvidenceState,
    canonical_evidence_type,
    evidence_from_raw_types,
    citizen_evidence_for,
    requirement_evidence_types,
)

if TYPE_CHECKING:
    from app.services.recommendation_service import CitizenContext

__all__ = [
    "EligibilityEvaluator",
    "get_eligibility_evaluator",
]


PASS = CriterionState.PASS
FAIL = CriterionState.FAIL
UNKNOWN = CriterionState.UNKNOWN
NOT_APPLICABLE = CriterionState.NOT_APPLICABLE

# The criterion vocabulary itself is owned by
# ``app.models.scheme_eligibility.CriterionState``. The aliases above exist
# only so existing importers keep working; new code should use CriterionState.

_NON_INDIVIDUAL_SCOPES = {"COMMUNITY", "STATE_UT", "LOCAL_BODY", "INSTITUTION"}
_REVIEW_STATUSES = {"review_required", "manual_review_required"}


def _norm(value: Any) -> str:
    """Lowercase, stripped string for matching.

    Underscores are normalized to spaces so that rule values like
    ``food_processing_entrepreneur`` match citizen occupations like
    ``food processing entrepreneur``.

    Handles Enum values by extracting their `.value` attribute.
    """
    if value is None:
        return ""
    # Handle Enum values
    if hasattr(value, "value"):
        value = value.value
    return str(value or "").strip().lower().replace("_", " ")


def _norm_set(values: Iterable[Any]) -> set[str]:
    return {_norm(v) for v in values if v}


def _text_contains(needle: str, haystack: str) -> bool:
    """Case-insensitive substring match."""
    return _norm(needle) in _norm(haystack)


class EligibilityEvaluator:
    """Evaluate a structured scheme eligibility rule against a citizen context."""

    def evaluate(
        self,
        scheme: SchemeEligibility,
        context: "CitizenContext",
    ) -> EligibilityResult:
        """Return the eligibility result for one scheme against one citizen."""
        conditions: List[EligibilityConditionResult] = []
        missing: List[EligibilityConditionResult] = []
        evidence_view = citizen_evidence_for(context)

        for condition, is_missing in self._evaluate_criteria(scheme, context):
            conditions.append(condition)
            if is_missing:
                missing.append(condition)

        matched = [c for c in conditions if c.passed]
        failed = [c for c in conditions if not c.passed and c not in missing]

        mandatory_conditions = [c for c in conditions if c.mandatory]
        mandatory_total = len(mandatory_conditions)
        mandatory_passed = sum(1 for c in mandatory_conditions if c.passed)

        eligibility_percentage = (
            round((mandatory_passed / mandatory_total) * 100.0, 2)
            if mandatory_total
            else 100.0
        )

        result = EligibilityResult(
            scheme_name=scheme.scheme_name,
            scheme_id=scheme.scheme_id,
            status="",
            matched_conditions=matched,
            failed_conditions=failed,
            missing_information=missing,
            evidence=list(scheme.evidence_sources or []),
            evidence_states=evidence_view.states,
            unmapped_document_types=list(evidence_view.unmapped_types),
            eligibility_percentage=eligibility_percentage,
            mandatory_rules_total=mandatory_total,
            mandatory_rules_passed=mandatory_passed,
        )
        result.status = determine_status(result)
        return result

    def evaluate_many(
        self,
        schemes: Iterable[SchemeEligibility],
        context: "CitizenContext",
    ) -> List[EligibilityResult]:
        """Evaluate multiple schemes against one citizen context."""
        return [self.evaluate(scheme, context) for scheme in schemes]

    def evaluate_catalogue_entry(
        self,
        entry: SchemeEligibilityCatalogueEntry,
        context: "CitizenContext",
    ) -> EligibilityResult:
        """Evaluate catalogue rules with deterministic PASS/FAIL/UNKNOWN semantics.

        Entries marked for review, entries without safe machine rules, and
        programme-level scopes are returned as ``insufficient_information`` with
        a manual-review condition. The project has no separate public
        ``manual_review_required`` eligibility status, so ``evaluation_status``
        carries that detail while preserving the established status vocabulary.
        """
        if self._requires_manual_review(entry):
            return self._manual_review_result(entry)

        conditions: List[EligibilityConditionResult] = [
            self._evaluate_catalogue_rule(entry, rule, context)
            for rule in entry.rules
        ]
        evidence_view = citizen_evidence_for(context)
        matched = [c for c in conditions if c.result in {PASS, NOT_APPLICABLE}]
        failed = [c for c in conditions if c.result == FAIL]
        missing = [c for c in conditions if c.result == UNKNOWN]

        mandatory_conditions = [
            c for c in conditions if c.mandatory and c.result != NOT_APPLICABLE
        ]
        mandatory_total = len(mandatory_conditions)
        mandatory_passed = sum(1 for c in mandatory_conditions if c.result == PASS)
        eligibility_percentage = (
            round((mandatory_passed / mandatory_total) * 100.0, 2)
            if mandatory_total
            else 0.0
        )

        result = EligibilityResult(
            scheme_name=entry.scheme_name,
            scheme_id=entry.scheme_id,
            status="",
            matched_conditions=matched,
            failed_conditions=failed,
            missing_information=missing,
            evidence=self._entry_evidence(entry),
            evidence_states=evidence_view.states,
            unmapped_document_types=list(evidence_view.unmapped_types),
            evidence_requirements=list(entry.evidence_requirements),
            missing_evidence=self._missing_evidence(entry, context),
            evaluation_status="evaluated",
            eligibility_percentage=eligibility_percentage,
            mandatory_rules_total=mandatory_total,
            mandatory_rules_passed=mandatory_passed,
        )
        result.status = determine_status(result)
        if result.status == EligibilityStatus.ELIGIBLE and result.missing_evidence:
            result.status = EligibilityStatus.POTENTIALLY_ELIGIBLE
        return result

    # ── Criterion evaluation ──────────────────────────────────────────────

    def _requires_manual_review(self, entry: SchemeEligibilityCatalogueEntry) -> bool:
        if not entry.eligibility_available:
            return True
        if entry.extraction_status in _REVIEW_STATUSES:
            return True
        if entry.beneficiary_scope in _NON_INDIVIDUAL_SCOPES:
            return True
        if not entry.rules:
            return True
        return False

    def _manual_review_result(self, entry: SchemeEligibilityCatalogueEntry) -> EligibilityResult:
        condition = EligibilityConditionResult(
            condition="manual_review_required",
            passed=False,
            actual_value=None,
            expected_value=entry.extraction_status,
            evidence=self._entry_evidence(entry),
            mandatory=True,
            rule_id=f"{entry.scheme_id}-manual-review",
            field="eligibility_catalogue",
            operator="manual_review",
            rule_type="SCHEME_SPECIFIC",
            result=UNKNOWN,
            notes=entry.notes,
            source_document=entry.pdf_filename,
        )
        return EligibilityResult(
            scheme_name=entry.scheme_name,
            scheme_id=entry.scheme_id,
            status=EligibilityStatus.INSUFFICIENT_INFORMATION,
            matched_conditions=[],
            failed_conditions=[],
            missing_information=[condition],
            evidence=self._entry_evidence(entry),
            evidence_requirements=list(entry.evidence_requirements),
            missing_evidence=[],
            evaluation_status="manual_review_required",
            eligibility_percentage=0.0,
            mandatory_rules_total=1,
            mandatory_rules_passed=0,
        )

    def _evaluate_catalogue_rule(
        self,
        entry: SchemeEligibilityCatalogueEntry,
        rule: StructuredEligibilityRule,
        context: "CitizenContext",
    ) -> EligibilityConditionResult:
        if rule.rule_type == "CONDITIONAL":
            return self._evaluate_conditional_rule(entry, rule, context)

        actual, value_known = self._resolve_rule_value(rule, context)
        result = UNKNOWN
        if value_known:
            result = PASS if self._compare_rule(actual, rule.operator, rule.value) else FAIL

        if rule.rule_type == "EXCLUSION" and result == PASS:
            notes = "Exclusion condition did not apply."
        elif rule.rule_type == "EXCLUSION" and result == FAIL:
            notes = "Exclusion condition applies."
        else:
            notes = rule.notes

        return self._catalogue_condition(entry, rule, actual, result, notes=notes)

    def _evaluate_conditional_rule(
        self,
        entry: SchemeEligibilityCatalogueEntry,
        rule: StructuredEligibilityRule,
        context: "CitizenContext",
    ) -> EligibilityConditionResult:
        when_result = self._evaluate_inline_expression(rule.when or {}, context)
        if when_result == FAIL:
            return self._catalogue_condition(
                entry,
                rule,
                actual=None,
                result=NOT_APPLICABLE,
                mandatory=False,
                notes="Conditional rule did not apply.",
            )
        if when_result == UNKNOWN:
            return self._catalogue_condition(
                entry,
                rule,
                actual=None,
                result=UNKNOWN,
                notes="Could not determine whether the conditional rule applies.",
            )

        requirement_result = self._evaluate_inline_expression(rule.requirement or {}, context)
        return self._catalogue_condition(
            entry,
            rule,
            actual=None,
            result=requirement_result,
            notes="Conditional rule applied; requirement evaluated.",
        )

    def _evaluate_inline_expression(self, expression: dict[str, Any], context: "CitizenContext") -> str:
        field = expression.get("profile_field") or expression.get("field")
        operator = expression.get("operator")
        expected = expression.get("value")
        actual, value_known = self._resolve_value(field, context)
        if not value_known:
            return UNKNOWN
        return PASS if self._compare_rule(actual, operator, expected) else FAIL

    def _resolve_rule_value(
        self,
        rule: StructuredEligibilityRule,
        context: "CitizenContext",
    ) -> tuple[Any, bool]:
        field = rule.profile_field or rule.field
        return self._resolve_value(field, context)

    def _resolve_value(self, field: Any, context: "CitizenContext") -> tuple[Any, bool]:
        if not field:
            return None, False

        field_name = str(field)
        if field_name in {"context.age", "age"}:
            return context.age, context.age is not None
        if field_name == "land_ownership":
            values = [getattr(record, "ownership_type", None) for record in context.land_records]
            values = [value for value in values if value not in (None, "")]
            return values, bool(values)
        if field_name == "land_area":
            values = [getattr(record, "land_area", None) for record in context.land_records]
            values = [value for value in values if value is not None]
            return values, bool(values)
        if field_name == "land_type":
            values = [getattr(record, "land_type", None) for record in context.land_records]
            values = [value for value in values if value not in (None, "")]
            return values, bool(values)

        root, _, attribute = field_name.partition(".")
        if root == "citizen":
            return self._object_value(context.citizen, attribute)
        if root == "profile":
            return self._object_value(context.profile, attribute)
        if root == "land_records":
            values = [getattr(record, attribute, None) for record in context.land_records]
            values = [value for value in values if value not in (None, "")]
            return values, bool(values)
        if hasattr(context, field_name):
            value = getattr(context, field_name)
            return value, value not in (None, "", [], {}, ())
        if hasattr(context.profile, field_name):
            return self._object_value(context.profile, field_name)
        if hasattr(context.citizen, field_name):
            return self._object_value(context.citizen, field_name)
        return None, False

    @staticmethod
    def _object_value(source: Any, attribute: str) -> tuple[Any, bool]:
        value = getattr(source, attribute, None)
        return value, value not in (None, "", [], {}, ())

    def _compare_rule(self, actual: Any, operator: Any, expected: Any) -> bool:
        operator = str(operator or "").lower()
        if operator in {"in", "any_of"}:
            return self._any_actual_in_expected(actual, expected)
        if operator == "all_of":
            return self._all_expected_in_actual(actual, expected)
        if operator == "not_in":
            return not self._any_actual_in_expected(actual, expected)
        if operator == "exists":
            return actual not in (None, "", [], {}, ())
        if operator == "not_exists":
            return actual in (None, "", [], {}, False)
        if operator in {"==", "!="}:
            equal = self._values_equal(actual, expected)
            return equal if operator == "==" else not equal
        if operator in {">", ">=", "<", "<="}:
            return self._compare_numeric(actual, operator, expected)
        return False

    def _any_actual_in_expected(self, actual: Any, expected: Any) -> bool:
        actual_values = self._as_list(actual)
        expected_values = self._as_list(expected)
        for actual_item in actual_values:
            for expected_item in expected_values:
                if self._values_equal(actual_item, expected_item):
                    return True
                if isinstance(actual_item, str) and isinstance(expected_item, str):
                    if _text_contains(actual_item, expected_item) or _text_contains(expected_item, actual_item):
                        return True
        return False

    def _all_expected_in_actual(self, actual: Any, expected: Any) -> bool:
        actual_values = self._as_list(actual)
        return all(self._any_actual_in_expected(actual_values, item) for item in self._as_list(expected))

    def _values_equal(self, actual: Any, expected: Any) -> bool:
        if isinstance(expected, bool):
            return self._to_bool(actual) is expected
        if isinstance(actual, bool):
            expected_bool = self._to_bool(expected)
            return expected_bool is not None and actual is expected_bool
        if isinstance(actual, list):
            return any(self._values_equal(item, expected) for item in actual)
        if isinstance(expected, list):
            return any(self._values_equal(actual, item) for item in expected)
        return _norm(actual) == _norm(expected)

    def _compare_numeric(self, actual: Any, operator: str, expected: Any) -> bool:
        expected_number = self._to_number(expected)
        if expected_number is None:
            return False
        for value in self._as_list(actual):
            actual_number = self._to_number(value)
            if actual_number is None:
                continue
            if operator == ">" and actual_number > expected_number:
                return True
            if operator == ">=" and actual_number >= expected_number:
                return True
            if operator == "<" and actual_number < expected_number:
                return True
            if operator == "<=" and actual_number <= expected_number:
                return True
        return False

    @staticmethod
    def _as_list(value: Any) -> list[Any]:
        if isinstance(value, list):
            return value
        if isinstance(value, set):
            return list(value)
        if isinstance(value, tuple):
            return list(value)
        return [value]

    @staticmethod
    def _to_number(value: Any) -> Optional[float]:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_bool(value: Any) -> Optional[bool]:
        if isinstance(value, bool):
            return value
        normalized = _norm(value)
        if normalized in {"true", "yes", "y", "1"}:
            return True
        if normalized in {"false", "no", "n", "0"}:
            return False
        return None

    def _catalogue_condition(
        self,
        entry: SchemeEligibilityCatalogueEntry,
        rule: StructuredEligibilityRule,
        actual: Any,
        result: str,
        mandatory: Optional[bool] = None,
        notes: Optional[str] = None,
    ) -> EligibilityConditionResult:
        if mandatory is None:
            mandatory = rule.severity != "optional"
        return EligibilityConditionResult(
            condition=rule.field,
            passed=result in {PASS, NOT_APPLICABLE},
            actual_value=actual,
            expected_value=rule.value,
            evidence=[self._rule_evidence(entry, rule)],
            mandatory=mandatory,
            rule_id=rule.rule_id,
            field=rule.field,
            operator=rule.operator,
            rule_type=rule.rule_type,
            result=result,
            notes=notes or rule.notes,
            source_document=rule.source.document,
        )

    @staticmethod
    def _rule_evidence(
        entry: SchemeEligibilityCatalogueEntry,
        rule: StructuredEligibilityRule,
    ) -> EvidenceSource:
        return EvidenceSource(
            chunk_id=rule.rule_id,
            scheme_id=entry.scheme_id,
            page_number=rule.source.page_number,
            section_name=rule.source.section_name,
            text=rule.source.text,
            document_id=rule.source.document,
        )

    @staticmethod
    def _entry_evidence(entry: SchemeEligibilityCatalogueEntry) -> list[EvidenceSource]:
        return [
            EvidenceSource(
                chunk_id=f"{entry.scheme_id}-catalogue",
                scheme_id=entry.scheme_id,
                document_id=entry.pdf_filename,
                section_name=entry.extraction_status,
                text=entry.notes,
            )
        ]

    def _missing_evidence(
        self,
        entry: SchemeEligibilityCatalogueEntry,
        context: "CitizenContext",
    ) -> list[str]:
        evidence = citizen_evidence_for(context)
        return evidence.missing_requirements(entry.evidence_requirements)

    def _evaluate_criteria(
        self,
        scheme: SchemeEligibility,
        context: CitizenContext,
    ) -> List[tuple[EligibilityConditionResult, bool]]:
        """Evaluate every criterion the scheme actually specifies.

        Returns a list of ``(condition, is_missing)`` tuples. A criterion is
        only included if the scheme rule actually specifies it.
        """
        results: List[tuple[EligibilityConditionResult, bool]] = []

        occupation = self._evaluate_occupation(scheme, context)
        if occupation is not None:
            results.append(occupation)

        age = self._evaluate_age(scheme, context)
        if age is not None:
            results.append(age)

        income = self._evaluate_income(scheme, context)
        if income is not None:
            results.append(income)

        land = self._evaluate_land(scheme, context)
        if land is not None:
            results.append(land)

        social = self._evaluate_social_category(scheme, context)
        if social is not None:
            results.append(social)

        state = self._evaluate_state(scheme, context)
        if state is not None:
            results.append(state)

        return results

    def _evaluate_occupation(
        self,
        scheme: SchemeEligibility,
        context: CitizenContext,
    ) -> Optional[tuple[EligibilityConditionResult, bool]]:
        """Occupation / target-group requirement (mandatory when specified)."""
        occupations = _norm_set(scheme.occupations)
        if not occupations:
            return None

        citizen_occupation = _norm(context.occupation)
        is_farmer = bool(getattr(context, "is_farmer", False))

        if not citizen_occupation and not is_farmer:
            return self._condition(
                scheme,
                "occupation",
                "Citizen occupation must match one of the scheme target occupations",
                expected=sorted(occupations),
                actual=None,
                passed=False,
                mandatory=True,
                missing=True,
            )

        matched = False
        for occupation in occupations:
            if occupation == "farmer" and is_farmer:
                matched = True
                break
            if citizen_occupation and (
                _text_contains(occupation, citizen_occupation)
                or _text_contains(citizen_occupation, occupation)
            ):
                matched = True
                break

        return self._condition(
            scheme,
            "occupation",
            "Citizen occupation must match one of the scheme's target occupations",
            expected=sorted(occupations),
            actual=context.occupation or None,
            passed=matched,
            mandatory=True,
            missing=False,
        )

    def _evaluate_age(
        self,
        scheme: SchemeEligibility,
        context: CitizenContext,
    ) -> Optional[tuple[EligibilityConditionResult, bool]]:
        """Age range requirement (mandatory when specified)."""
        if scheme.age_min is None and scheme.age_max is None:
            return None

        age = context.age
        if age is None:
            return self._condition(
                scheme,
                "age",
                "Citizen age must be within the scheme's age range",
                expected=self._age_range(scheme),
                actual=None,
                passed=False,
                mandatory=True,
                missing=True,
            )

        passed = True
        if scheme.age_min is not None and age < scheme.age_min:
            passed = False
        if scheme.age_max is not None and age > scheme.age_max:
            passed = False

        return self._condition(
            scheme,
            "age",
            "Citizen age must be within the scheme's age range",
            expected=self._age_range(scheme),
            actual=age,
            passed=passed,
            mandatory=True,
            missing=False,
        )

    def _evaluate_income(
        self,
        scheme: SchemeEligibility,
        context: CitizenContext,
    ) -> Optional[tuple[EligibilityConditionResult, bool]]:
        """Income cap and income-category exclusions (mandatory when specified)."""
        has_income_cap = scheme.income_max is not None
        has_exclusions = bool(scheme.income_category_exclusions)
        if not has_income_cap and not has_exclusions:
            return None

        annual_income = getattr(context.profile, "annual_income", None)
        income_known = annual_income is not None

        # Income cap.
        if has_income_cap:
            if not income_known:
                return self._condition(
                    scheme,
                    "income",
                    "Annual income must not exceed the scheme's income cap",
                    expected=scheme.income_max,
                    actual=None,
                    passed=False,
                    mandatory=True,
                    missing=True,
                )
            passed = float(annual_income) <= float(scheme.income_max)
            return self._condition(
                scheme,
                "income",
                "Annual income must not exceed the scheme's income cap",
                expected=scheme.income_max,
                actual=float(annual_income),
                passed=passed,
                mandatory=True,
                missing=False,
            )

        # Income-category exclusions (e.g. income-tax payer, government employee).
        # Only exclusions representable in the profile are evaluated; the rest
        # are reported as missing information (cannot be determined).
        income_category = _norm(getattr(context.profile, "income_category", None))
        representable = _norm_set(scheme.income_category_exclusions)
        if not income_category:
            return self._condition(
                scheme,
                "income_category",
                "Citizen income category must not be in the scheme's exclusion list",
                expected=sorted(representable),
                actual=None,
                passed=False,
                mandatory=True,
                missing=True,
            )

        excluded = income_category in representable
        return self._condition(
            scheme,
            "income_category",
            "Citizen income category must not be in the scheme's exclusion list",
            expected=sorted(representable),
            actual=income_category,
            passed=not excluded,
            mandatory=True,
            missing=False,
        )

    def _evaluate_land(
        self,
        scheme: SchemeEligibility,
        context: CitizenContext,
    ) -> Optional[tuple[EligibilityConditionResult, bool]]:
        """Land requirement (mandatory when specified).

        Uses "any land record satisfies" semantics: the requirement is met if
        ANY of the citizen's land records satisfies the scheme's land criteria.
        If the citizen has no land records loaded, the condition is reported as
        missing information (not a failure).
        """
        if scheme.land_required is None:
            return None

        if scheme.land_required is False:
            return self._condition(
                scheme,
                "land",
                "No land ownership is required for this scheme",
                expected="no land required",
                actual="no land required",
                passed=True,
                mandatory=True,
                missing=False,
            )

        # land_required is True.
        land_records = list(getattr(context, "land_records", []) or [])
        if not land_records:
            return self._condition(
                scheme,
                "land",
                "Citizen must own/lease qualifying land for this scheme",
                expected=self._land_requirement_text(scheme),
                actual=None,
                passed=False,
                mandatory=True,
                missing=True,
            )

        # Evaluate against ANY record.
        required_types = _norm_set(scheme.land_type)
        required_ownership = _norm_set(scheme.land_ownership_types)
        min_acres = scheme.land_min_acres
        max_acres = scheme.land_max_acres

        satisfied = False
        inconclusive = False
        for record in land_records:
            record_type = _norm(getattr(record, "land_type", None))
            record_ownership = _norm(getattr(record, "ownership_type", None))
            record_area = getattr(record, "land_area", None)

            # A land record whose required attributes are UNKNOWN (not digitized)
            # cannot be evaluated against the scheme requirement. Per the design
            # rules, "data absent" is missing information — NOT a failure. Only a
            # record with KNOWN attributes that do not satisfy the requirement is
            # a definitive failure.
            type_unknown = bool(required_types) and not record_type
            ownership_unknown = bool(required_ownership) and not record_ownership

            # Definitive rejections first: KNOWN value that does not qualify.
            if required_ownership and not ownership_unknown and record_ownership not in required_ownership:
                continue
            if required_types and not type_unknown and not self._land_type_matches(record_type, required_types):
                continue
            if min_acres is not None and record_area is not None and float(record_area) < float(min_acres):
                continue
            if max_acres is not None and record_area is not None and float(record_area) > float(max_acres):
                continue

            # Record satisfies every KNOWN criterion, but some required
            # attribute is unknown → inconclusive (pending information).
            if type_unknown or ownership_unknown:
                inconclusive = True
                continue
            if (min_acres is not None or max_acres is not None) and record_area is None:
                inconclusive = True
                continue

            satisfied = True
            break

        if satisfied:
            passed, is_missing = True, False
        elif inconclusive:
            # At least one record might qualify but the data is incomplete.
            passed, is_missing = False, True
        else:
            # Every record was fully evaluated and none satisfies the requirement.
            passed, is_missing = False, False

        return self._condition(
            scheme,
            "land",
            "Citizen must own/lease qualifying land for this scheme",
            expected=self._land_requirement_text(scheme),
            actual=self._land_actual_text(land_records),
            passed=passed,
            mandatory=True,
            missing=is_missing,
        )

    def _evaluate_social_category(
        self,
        scheme: SchemeEligibility,
        context: CitizenContext,
    ) -> Optional[tuple[EligibilityConditionResult, bool]]:
        """Social-category / beneficiary-group preference (non-mandatory).

        Priority groups (SC/ST/women/small farmer, etc.) are treated as
        PREFERENCES, not mandatory eligibility requirements. A citizen not in a
        priority group is NOT made ineligible by this alone.
        """
        if not scheme.social_categories:
            return None

        categories = _norm_set(scheme.social_categories)
        caste = _norm(context.caste)
        community = _norm(context.community)
        gender = _norm(getattr(context.citizen, "gender", None))
        is_farmer = bool(getattr(context, "is_farmer", False))

        matched = False
        for category in categories:
            if category in {"sc", "st", "obc", "bc", "mbc"} and (
                _text_contains(category, caste) or _text_contains(category, community)
            ):
                matched = True
                break
            if category in {"women", "female"} and gender in {"female", "women"}:
                matched = True
                break
            if category in {"small_farmer", "marginal_farmer", "small_marginal_farmer"} and is_farmer:
                matched = True
                break
            if _text_contains(category, caste) or _text_contains(category, community):
                matched = True
                break

        return self._condition(
            scheme,
            "social_category",
            "Citizen belongs to a preferred beneficiary group (preference, not mandatory)",
            expected=sorted(categories),
            actual=caste or community or gender or None,
            passed=matched,
            mandatory=False,
            missing=False,
        )

    def _evaluate_state(
        self,
        scheme: SchemeEligibility,
        context: CitizenContext,
    ) -> Optional[tuple[EligibilityConditionResult, bool]]:
        """Geographic (state) restriction (mandatory when specified)."""
        if not scheme.states:
            return None

        citizen_state = _norm(context.state)
        if not citizen_state:
            return self._condition(
                scheme,
                "state",
                "Citizen state must be in the scheme's eligible states",
                expected=sorted(_norm_set(scheme.states)),
                actual=None,
                passed=False,
                mandatory=True,
                missing=True,
            )

        passed = citizen_state in _norm_set(scheme.states)
        return self._condition(
            scheme,
            "state",
            "Citizen state must be in the scheme's eligible states",
            expected=sorted(_norm_set(scheme.states)),
            actual=context.state,
            passed=passed,
            mandatory=True,
            missing=False,
        )

    def _condition(
        self,
        scheme: SchemeEligibility,
        condition: str,
        description: str,
        expected: Any,
        actual: Any,
        passed: bool,
        mandatory: bool,
        missing: bool,
    ) -> tuple[EligibilityConditionResult, bool]:
        """Build an EligibilityConditionResult with scheme evidence attached."""
        return (
            EligibilityConditionResult(
                condition=condition,
                passed=passed,
                actual_value=actual,
                expected_value=expected,
                evidence=list(scheme.evidence_sources or []),
                mandatory=mandatory,
            ),
            missing,
        )

    @staticmethod
    def _age_range(scheme: SchemeEligibility) -> str:
        if scheme.age_min is not None and scheme.age_max is not None:
            return f"{scheme.age_min}-{scheme.age_max}"
        if scheme.age_min is not None:
            return f">= {scheme.age_min}"
        if scheme.age_max is not None:
            return f"<= {scheme.age_max}"
        return "any"

    @staticmethod
    def _land_type_matches(record_type: str, required_types: set[str]) -> bool:
        """Return True if a land record type satisfies the scheme's required types.

        Treats ``cultivable`` and ``agricultural`` as equivalent, since the
        structured rules use "cultivable" while the LandRecord model uses the
        ``LandType.AGRICULTURAL`` enum value.
        """
        if not required_types:
            return True
        if record_type in required_types:
            return True
        if record_type == "agricultural" and "cultivable" in required_types:
            return True
        if record_type == "cultivable" and "agricultural" in required_types:
            return True
        return False

    @staticmethod
    def _land_requirement_text(scheme: SchemeEligibility) -> str:
        parts: List[str] = []
        if scheme.land_type:
            parts.append("type=" + ",".join(scheme.land_type))
        if scheme.land_ownership_types:
            parts.append("ownership=" + ",".join(scheme.land_ownership_types))
        if scheme.land_min_acres is not None:
            parts.append(f"min={scheme.land_min_acres} acres")
        if scheme.land_max_acres is not None:
            parts.append(f"max={scheme.land_max_acres} acres")
        return "; ".join(parts) if parts else "qualifying land"

    @staticmethod
    def _land_actual_text(records: List[Any]) -> str:
        summaries = []
        for record in records:
            parts = []
            if getattr(record, "land_type", None):
                parts.append(str(record.land_type))
            if getattr(record, "ownership_type", None):
                parts.append(str(record.ownership_type))
            if getattr(record, "land_area", None) is not None:
                parts.append(f"{record.land_area} acres")
            summaries.append(" ".join(parts) if parts else "land record")
        return "; ".join(summaries)


def get_eligibility_evaluator() -> EligibilityEvaluator:
    """Return a shared EligibilityEvaluator instance."""
    return EligibilityEvaluator()
