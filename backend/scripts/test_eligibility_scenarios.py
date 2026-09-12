"""Manual eligibility scenario runner.

This script is an investigation aid, not a permanent pytest suite. It exercises
the actual catalogue loader and EligibilityEvaluator against synthetic citizen
profiles so PASS/FAIL/UNKNOWN, exclusions, missing evidence, and manual-review
cases can be inspected from one command.

Run from backend/:
    python scripts/test_eligibility_scenarios.py
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Iterable


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.models.scheme_eligibility import EligibilityResult  # noqa: E402
from app.services.eligibility_catalog_service import get_catalogue_entry  # noqa: E402
from app.services.eligibility_evaluator import EligibilityEvaluator  # noqa: E402
from app.services.recommendation_service import CitizenContext  # noqa: E402


@dataclass(frozen=True)
class Scenario:
    name: str
    context: CitizenContext
    scheme_ids: tuple[str, ...]
    note: str


def make_land_record(
    *,
    ownership_type: str | None = "owned",
    land_area: float | None = 2.5,
    land_type: str | None = "agricultural",
) -> SimpleNamespace:
    return SimpleNamespace(
        land_type=land_type,
        ownership_type=ownership_type,
        land_area=land_area,
        survey_number="123/4" if land_area is not None else None,
        district="Villupuram",
        state="Tamil Nadu",
    )


def make_context(
    *,
    age: int | None,
    occupation: str | None,
    annual_income: float | None,
    land_records: list[SimpleNamespace],
    gender: str = "male",
    government_employee: bool | None = None,
    income_tax_payer: bool | None = None,
    document_types: Iterable[str] = (),
) -> CitizenContext:
    normalized_occupation = (occupation or "").lower()
    profile = SimpleNamespace(
        occupation=occupation,
        annual_income=annual_income,
        income_category="bpl" if annual_income is not None and annual_income <= 200000 else None,
        is_farmer=bool(
            "farmer" in normalized_occupation or "cultivator" in normalized_occupation
        ),
        caste="",
        community="",
        education_level="10th",
        family_member_count=4,
        profile_completion_percentage=85,
        government_employee=government_employee,
        income_tax_payer=income_tax_payer,
    )
    citizen = SimpleNamespace(
        id="synthetic-citizen",
        full_name="Synthetic Citizen",
        gender=gender,
        state="Tamil Nadu",
        district="Villupuram",
        village="Sample Village",
    )
    known_land_area = sum(
        float(record.land_area)
        for record in land_records
        if getattr(record, "land_area", None) is not None
    )
    return CitizenContext(
        citizen=citizen,
        profile=profile,
        land_records=land_records,
        documents=[],
        total_land_area=known_land_area,
        profile_completion_percentage=85,
        age=age,
        senior_citizen=bool(age is not None and age >= 60),
        family_size=4,
        document_types=set(document_types),
        document_names=set(),
    )


def build_scenarios() -> list[Scenario]:
    complete_farmer_docs = {
        "aadhaar",
        "land record",
        "lease agreement",
        "bank account",
        "caste certificate",
    }
    likely_eligible_farmer = make_context(
        age=35,
        occupation="cultivator farmer",
        annual_income=150000,
        government_employee=False,
        income_tax_payer=False,
        land_records=[make_land_record()],
        document_types=complete_farmer_docs,
    )
    deliberately_failing_farmer = make_context(
        age=16,
        occupation="cultivator farmer",
        annual_income=150000,
        government_employee=False,
        income_tax_payer=False,
        land_records=[make_land_record()],
        document_types=complete_farmer_docs,
    )
    incomplete_farmer = make_context(
        age=35,
        occupation="farmer",
        annual_income=None,
        government_employee=None,
        income_tax_payer=None,
        land_records=[],
        document_types={"aadhaar"},
    )
    exclusion_profile = make_context(
        age=35,
        occupation="farmer",
        annual_income=150000,
        government_employee=False,
        income_tax_payer=True,
        land_records=[make_land_record()],
        document_types=complete_farmer_docs,
    )
    manual_review_profile = make_context(
        age=35,
        occupation="farmer",
        annual_income=150000,
        government_employee=False,
        income_tax_payer=False,
        land_records=[make_land_record()],
        document_types=complete_farmer_docs,
    )
    missing_evidence_farmer = make_context(
        age=35,
        occupation="farmer",
        annual_income=150000,
        government_employee=False,
        income_tax_payer=False,
        land_records=[make_land_record()],
        document_types={"aadhaar"},
    )

    return [
        Scenario(
            name="PROFILE A: likely eligible farmer",
            context=likely_eligible_farmer,
            scheme_ids=("pm-kusum", "smam", "pm-kisan"),
            note="Known matching farmer/land values with full farmer evidence.",
        ),
        Scenario(
            name="PROFILE B: deliberately failing farmer",
            context=deliberately_failing_farmer,
            scheme_ids=("pm-vishwakarma", "pmfme"),
            note="Age 16 is evaluated only against actual catalogue age-threshold rules.",
        ),
        Scenario(
            name="PROFILE C: incomplete farmer",
            context=incomplete_farmer,
            scheme_ids=("pm-kisan", "pm-kusum"),
            note="Land, income-tax, and several evidence facts are intentionally unknown/missing.",
        ),
        Scenario(
            name="PROFILE D: exclusion scenario",
            context=exclusion_profile,
            scheme_ids=("pm-kisan",),
            note="Uses the actual pm-kisan-income-tax-exclusion rule.",
        ),
        Scenario(
            name="PROFILE E: manual-review / non-individual programme",
            context=manual_review_profile,
            scheme_ids=("pm-svanidhi", "jjm"),
            note="PM-SVANidhi is manual-review; JJM is a community-scope programme.",
        ),
        Scenario(
            name="PROFILE F: missing evidence separation",
            context=missing_evidence_farmer,
            scheme_ids=("smam",),
            note="Eligibility facts pass, but evidence documents are intentionally incomplete.",
        ),
    ]


def condition_lines(conditions) -> list[str]:
    lines = []
    for condition in conditions:
        source_bits = [
            condition.source_document or "",
            condition.evidence[0].section_name if condition.evidence else "",
        ]
        source = " / ".join(bit for bit in source_bits if bit)
        lines.append(
            "    - "
            f"{condition.result or ('PASS' if condition.passed else 'FAIL')} "
            f"{condition.rule_id or condition.condition}: "
            f"field={condition.field or condition.condition}, "
            f"operator={condition.operator}, "
            f"expected={condition.expected_value!r}, "
            f"actual={condition.actual_value!r}, "
            f"mandatory={condition.mandatory}"
            + (f", source={source}" if source else "")
        )
    return lines


def print_result(scenario: Scenario, scheme_id: str, result: EligibilityResult, scope: str) -> None:
    print("=" * 88)
    print(f"Profile: {scenario.name}")
    print(f"Scenario note: {scenario.note}")
    print(f"Scheme: {result.scheme_name} ({scheme_id})")
    print(f"Beneficiary scope: {scope}")
    print(f"Final eligibility status: {result.status}")
    print(f"Evaluation status: {result.evaluation_status}")
    print(f"Eligibility percentage: {result.eligibility_percentage}")

    print("Passed rules:")
    print("\n".join(condition_lines(result.matched_conditions)) or "    - none")

    print("Failed rules:")
    print("\n".join(condition_lines(result.failed_conditions)) or "    - none")

    print("Unknown rules / missing profile information:")
    print("\n".join(condition_lines(result.missing_information)) or "    - none")

    print(f"Missing evidence: {result.missing_evidence or []}")
    manual_reason = next(
        (condition.notes for condition in result.missing_information if condition.operator == "manual_review"),
        None,
    )
    if manual_reason:
        print(f"Manual-review reason: {manual_reason}")


def collect_suspicious_mappings(result: EligibilityResult) -> list[str]:
    suspicious = []
    for condition in result.failed_conditions + result.missing_information:
        if condition.result == "UNKNOWN" and condition.rule_type != "SCHEME_SPECIFIC":
            source = condition.evidence[0] if condition.evidence else None
            suspicious.append(
                f"{result.scheme_id} | {condition.rule_id} | "
                f"field={condition.field} | operator={condition.operator} | "
                f"source={getattr(source, 'document_id', None)} / {getattr(source, 'section_name', None)}"
            )
    return suspicious


def main() -> int:
    evaluator = EligibilityEvaluator()
    suspicious: list[str] = []

    for scenario in build_scenarios():
        for scheme_id in scenario.scheme_ids:
            entry = get_catalogue_entry(scheme_id)
            if entry is None:
                print(f"Missing catalogue entry for {scheme_id}")
                suspicious.append(f"{scheme_id} | missing catalogue entry")
                continue

            result = evaluator.evaluate_catalogue_entry(entry, scenario.context)
            print_result(scenario, scheme_id, result, entry.beneficiary_scope)
            suspicious.extend(collect_suspicious_mappings(result))

    print("=" * 88)
    print("Suspicious or review-worthy mappings observed:")
    if suspicious:
        for item in sorted(set(suspicious)):
            print(f"  - {item}")
    else:
        print("  - none")

    print("=" * 88)
    print("Manual runner complete. No production code or catalogue mutation was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
