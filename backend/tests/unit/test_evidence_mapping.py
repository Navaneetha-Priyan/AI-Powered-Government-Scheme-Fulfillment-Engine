"""Tests for the centralized evidence-requirement mapping."""
from __future__ import annotations

from app.services.evidence_mapping_service import (
    SUPPORTED_DOCUMENT_TYPES,
    get_mapping,
    humanize_requirement,
    manual_requirements_in_catalogue,
    resolve_evidence_checklist,
    supported_mappings,
)
from app.services.eligibility_catalog_service import load_eligibility_catalogue


def test_task_examples_map_to_upload_slots():
    assert get_mapping("identity_proof").document_types == ("aadhaar_card",)
    assert "smart_ration_card" in get_mapping("address_proof").document_types
    assert get_mapping("farmer_registration").document_types == ("farmer_document",)
    assert get_mapping("land_ownership_proof").document_types == ("land_document",)
    assert get_mapping("community_certificate").document_types == (
        "community_certificate",
    )
    assert get_mapping("income_proof").document_types == ("income_certificate",)
    for mapping in supported_mappings():
        assert set(mapping.document_types) <= SUPPORTED_DOCUMENT_TYPES


def test_satisfaction_needs_explicit_accepted_upload():
    items = resolve_evidence_checklist(["identity_proof"], {"bank_passbook"})
    assert items[0].status == "needed"
    items = resolve_evidence_checklist(["identity_proof"], {"aadhaar_card"})
    assert items[0].status == "available"
    assert items[0].matched_document_type == "aadhaar_card"


def test_profile_info_never_routes_to_upload():
    mapping = get_mapping("income_tax_payer")
    assert mapping.kind == "profile_info"
    assert mapping.profile_prompt == "Are you an income-tax payer?"
    items = resolve_evidence_checklist(
        ["income_tax_payer"], {"aadhaar_card", "bank_passbook"}
    )
    assert items[0].kind == "profile_info"
    assert items[0].status == "needed"
    assert items[0].document_types == []


def test_unknown_requirement_is_manual_not_hidden():
    items = resolve_evidence_checklist(["trader_license"], {"aadhaar_card"})
    assert len(items) == 1
    assert items[0].kind == "manual"
    assert items[0].status == "manual"
    assert "required" in (items[0].note or "").lower()


def test_humanize_never_leaks_snake_case():
    assert humanize_requirement("income_tax_payer") == "Income-tax payer status"
    assert humanize_requirement("farmer_registration") == "Farmer ID"
    assert "_" not in humanize_requirement("some_new_scheme_evidence")


def test_catalogue_manual_requirements_reported():
    manual = manual_requirements_in_catalogue(load_eligibility_catalogue())
    assert isinstance(manual, list)
    # Spot-check known non-upload evidence keys present in catalog.json.
    assert "trader_license" in manual or "bank_account" not in manual
