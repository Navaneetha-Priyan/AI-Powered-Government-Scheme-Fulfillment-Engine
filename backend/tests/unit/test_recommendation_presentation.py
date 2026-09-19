import pytest

from app.schemas.recommendation import EligibilityCheckResponse
from app.services.recommendation_service import _condition_counts


def _cond(
    result: str | None = None,
    passed: bool | None = None,
    mandatory: bool | None = None,
    severity: str | None = None,
) -> dict:
    item: dict = {}
    if result is not None:
        item["result"] = result
    if passed is not None:
        item["passed"] = passed
    if mandatory is not None:
        item["mandatory"] = mandatory
    if severity is not None:
        item["severity"] = severity
    return item


def test_condition_counts_mixed_results():
    matched = [_cond(result="PASS"), _cond(result="PASS")]
    missing = [_cond(result="FAIL"), _cond(result="UNKNOWN")]
    assert _condition_counts(matched, missing) == (2, 4)


def test_condition_counts_excludes_optional_and_not_applicable():
    matched = [
        _cond(result="PASS"),
        _cond(result="PASS", mandatory=False),
        _cond(result="PASS", severity="optional"),
        _cond(result="NOT_APPLICABLE", passed=True),
    ]
    missing = [_cond(result="UNKNOWN")]
    # Only the first PASS and the UNKNOWN are citizen-presentable.
    assert _condition_counts(matched, missing) == (1, 2)


def test_condition_counts_legacy_payloads_use_passed_flag():
    # Legacy rule-engine serializer: no `result`, only `passed`/`severity`.
    matched = [_cond(passed=True), _cond(passed=True)]
    missing = [_cond(passed=False), _cond(passed=False, severity="optional")]
    assert _condition_counts(matched, missing) == (2, 3)


def test_condition_counts_empty():
    assert _condition_counts([], []) == (0, 0)


def test_eligibility_check_response_accepts_additive_fields():
    response = EligibilityCheckResponse(
        citizen_id="c-1",
        evaluated_at="2026-01-01T00:00:00",
        total_rules=4,
        passed_rules=3,
        eligibility_percentage=75.0,
        eligible=False,
        eligibility_status="potentially_eligible",
        matched_rules=[],
        missing_requirements=[],
        required_documents=["land_record"],
        application_ready=False,
        reasoning="",
        mandatory_rules_total=4,
        mandatory_rules_passed=3,
        evidence_checklist=[
            {
                "requirement": "land_record",
                "label": "Land record",
                "kind": "document",
                "status": "needed",
            }
        ],
    )
    assert response.mandatory_rules_total == 4
    assert response.mandatory_rules_passed == 3
    assert response.evidence_checklist[0]["label"] == "Land record"


def test_eligibility_check_response_defaults_keep_old_clients_working():
    response = EligibilityCheckResponse(
        citizen_id="c-1",
        evaluated_at="2026-01-01T00:00:00",
        total_rules=1,
        passed_rules=1,
        eligibility_percentage=100.0,
        eligible=True,
        eligibility_status="eligible",
        matched_rules=[],
        missing_requirements=[],
        required_documents=[],
        application_ready=True,
        reasoning="",
    )
    assert response.mandatory_rules_total == 0
    assert response.mandatory_rules_passed == 0
    assert response.evidence_checklist is None