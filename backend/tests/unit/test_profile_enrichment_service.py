"""Unit/Integration Tests for ProfileEnrichmentService (Step 4).

These tests exercise the full persistence path: they build a citizen via the
real repositories, then call ``ProfileEnrichmentService`` with
``MappedDocumentData`` (as produced by Step 3 ``DocumentProfileMapper``) and
assert on the resulting persisted state and the returned ``EnrichmentResult``.

The service consumes only ``MappedDocumentData`` — never raw document metadata —
so these tests construct ``MappedDocumentData`` directly (the mapper is already
covered by its own Step 3 tests).
"""
from __future__ import annotations

from datetime import datetime

import pytest

from app.repositories.citizen_repository import CitizenRepository
from app.repositories.citizen_profile_repository import (
    CitizenProfileRepository,
    LandRecordRepository,
)
from app.schemas.citizen_profile import DocumentTypeEnum
from app.schemas.document_profile import (
    EnrichmentResult,
    LandRecordUpdateData,
    MappedDocumentData,
)
from app.services.profile_enrichment_service import ProfileEnrichmentService
from app.exceptions.exceptions import NotFoundError


# ── Helpers ───────────────────────────────────────────────────────────────────

def _create_citizen(db, **overrides):
    """Create a minimal citizen via the real repository."""
    data = {
        "email": "selvam@example.com",
        "phone": "9876543210",
        "password_hash": "hashed",
        "full_name": "Selvam Murugan",
        "district": "Villupuram",
        "state": "Tamil Nadu",
    }
    data.update(overrides)
    return CitizenRepository(db).create(data)


def _mapped(
    doc_type: DocumentTypeEnum,
    citizen_updates: dict = None,
    profile_updates: dict = None,
    land_updates: list = None,
    doc_id: str = None,
) -> MappedDocumentData:
    return MappedDocumentData(
        document_type=doc_type,
        document_id=doc_id,
        citizen_updates=citizen_updates or {},
        profile_updates=profile_updates or {},
        land_record_updates=land_updates or [],
    )


def _land(survey: str, **kw) -> LandRecordUpdateData:
    data = {"survey_number": survey}
    data.update(kw)
    return LandRecordUpdateData(**data)


def _aadhaar(full_name="Selvam Murugan", dob="1985-04-12", district="Villupuram"):
    return _mapped(
        DocumentTypeEnum.AADHAAR,
        citizen_updates={
            "full_name": full_name,
            "date_of_birth": dob,
            "gender": "male",
            "address_line1": "Main Road",
            "village": "Periyakulam",
            "taluk": "Villupuram",
            "district": district,
            "state": "Tamil Nadu",
            "pincode": "605602",
        },
        doc_id="doc-aadhaar",
    )


# ── Basic enrichment ──────────────────────────────────────────────────────────

class TestBasicEnrichment:
    def test_aadhaar_updates_citizen_fields(self, test_db):
        citizen = _create_citizen(test_db)
        service = ProfileEnrichmentService(test_db)

        result = service.enrich(citizen.id, _aadhaar())

        refreshed = CitizenRepository(test_db).get_by_id(citizen.id)
        assert refreshed.full_name == "Selvam Murugan"
        assert refreshed.district == "Villupuram"
        assert result.updated_citizen_fields
        assert "full_name" in result.updated_citizen_fields
        assert result.profile_completion_percentage > 0

    def test_income_certificate_updates_profile_income(self, test_db):
        citizen = _create_citizen(test_db)
        service = ProfileEnrichmentService(test_db)

        result = service.enrich(
            citizen.id,
            _mapped(
                DocumentTypeEnum.INCOME_CERTIFICATE,
                profile_updates={"annual_income": 72000.0, "income_category": "bpl"},
                doc_id="doc-income",
            ),
        )

        profile = CitizenProfileRepository(test_db).get_by_citizen_id(citizen.id)
        assert profile.annual_income == 72000.0
        assert profile.income_category == "bpl"
        assert "annual_income" in result.updated_profile_fields

    def test_caste_certificate_updates_caste_community(self, test_db):
        citizen = _create_citizen(test_db)
        service = ProfileEnrichmentService(test_db)

        service.enrich(
            citizen.id,
            _mapped(
                DocumentTypeEnum.CASTE_CERTIFICATE,
                profile_updates={
                    "caste": "Vanniyar",
                    "community": "MBC",
                    "sub_caste": "Padayachi",
                },
                doc_id="doc-caste",
            ),
        )

        profile = CitizenProfileRepository(test_db).get_by_citizen_id(citizen.id)
        assert profile.caste == "Vanniyar"
        assert profile.community == "MBC"
        assert profile.sub_caste == "Padayachi"
        assert profile.is_farmer is False

    def test_farmer_id_updates_farmer_information(self, test_db):
        citizen = _create_citizen(test_db)
        service = ProfileEnrichmentService(test_db)

        service.enrich(
            citizen.id,
            _mapped(
                DocumentTypeEnum.FARMER_ID,
                profile_updates={
                    "farmer_id": "TN-FARMER-001234",
                    "is_farmer": True,
                    "occupation": "Farmer",
                },
                doc_id="doc-farmer",
            ),
        )

        profile = CitizenProfileRepository(test_db).get_by_citizen_id(citizen.id)
        assert profile.is_farmer is True
        assert profile.farmer_id == "TN-FARMER-001234"
        assert profile.occupation == "Farmer"

    def test_ration_card_updates_ration_and_family(self, test_db):
        citizen = _create_citizen(test_db)
        service = ProfileEnrichmentService(test_db)

        service.enrich(
            citizen.id,
            _mapped(
                DocumentTypeEnum.SMART_RATION_CARD,
                citizen_updates={"smart_ration_card": "TN1234567890"},
                profile_updates={"family_member_count": 5},
                doc_id="doc-ration",
            ),
        )

        refreshed = CitizenRepository(test_db).get_by_id(citizen.id)
        profile = CitizenProfileRepository(test_db).get_by_citizen_id(citizen.id)
        assert refreshed.smart_ration_card == "TN1234567890"
        assert profile.family_member_count == 5

    def test_residence_certificate_updates_address(self, test_db):
        citizen = _create_citizen(test_db)
        service = ProfileEnrichmentService(test_db)

        service.enrich(
            citizen.id,
            _mapped(
                DocumentTypeEnum.RESIDENCE_CERTIFICATE,
                citizen_updates={
                    "village": "Periyakulam",
                    "taluk": "Villupuram",
                    "district": "Villupuram",
                    "state": "Tamil Nadu",
                },
                doc_id="doc-residence",
            ),
        )

        refreshed = CitizenRepository(test_db).get_by_id(citizen.id)
        assert refreshed.village == "Periyakulam"
        assert refreshed.taluk == "Villupuram"

    def test_disability_certificate_updates_disability(self, test_db):
        citizen = _create_citizen(test_db)
        service = ProfileEnrichmentService(test_db)

        service.enrich(
            citizen.id,
            _mapped(
                DocumentTypeEnum.DISABILITY_CERTIFICATE,
                profile_updates={"is_disabled": True, "disability_percentage": 45},
                doc_id="doc-disability",
            ),
        )

        profile = CitizenProfileRepository(test_db).get_by_citizen_id(citizen.id)
        assert profile.is_disabled is True
        assert profile.disability_percentage == 45

    def test_land_record_creates_a_land_record(self, test_db):
        citizen = _create_citizen(test_db)
        service = ProfileEnrichmentService(test_db)

        result = service.enrich(
            citizen.id,
            _mapped(
                DocumentTypeEnum.LAND_RECORD,
                land_updates=[
                    _land("123/2A", land_area=2.5, land_area_unit="acres")
                ],
                doc_id="doc-land",
            ),
        )

        records = LandRecordRepository(test_db).get_by_citizen_id(citizen.id)
        assert len(records) == 1
        assert records[0].survey_number == "123/2A"
        assert records[0].land_area == 2.5
        assert result.created_land_records == ["123/2A"]


# ── Incremental enrichment ────────────────────────────────────────────────────

class TestIncrementalEnrichment:
    def test_aadhaar_followed_by_income_preserves_aadhaar_fields(self, test_db):
        citizen = _create_citizen(test_db)
        service = ProfileEnrichmentService(test_db)

        service.enrich(citizen.id, _aadhaar())
        service.enrich(
            citizen.id,
            _mapped(
                DocumentTypeEnum.INCOME_CERTIFICATE,
                profile_updates={"annual_income": 72000.0, "income_category": "bpl"},
            ),
        )

        refreshed = CitizenRepository(test_db).get_by_id(citizen.id)
        profile = CitizenProfileRepository(test_db).get_by_citizen_id(citizen.id)
        # Aadhaar fields preserved.
        assert refreshed.full_name == "Selvam Murugan"
        assert refreshed.district == "Villupuram"
        # Income added.
        assert profile.annual_income == 72000.0

    def test_aadhaar_followed_by_land_preserves_previous_profile(self, test_db):
        citizen = _create_citizen(test_db)
        service = ProfileEnrichmentService(test_db)

        service.enrich(citizen.id, _aadhaar())
        service.enrich(
            citizen.id,
            _mapped(
                DocumentTypeEnum.INCOME_CERTIFICATE,
                profile_updates={"annual_income": 72000.0},
            ),
        )
        service.enrich(
            citizen.id,
            _mapped(
                DocumentTypeEnum.LAND_RECORD,
                land_updates=[
                    _land("123/2A", land_area=2.5, land_area_unit="acres")
                ],
            ),
        )

        refreshed = CitizenRepository(test_db).get_by_id(citizen.id)
        profile = CitizenProfileRepository(test_db).get_by_citizen_id(citizen.id)
        records = LandRecordRepository(test_db).get_by_citizen_id(citizen.id)
        assert refreshed.full_name == "Selvam Murugan"
        assert profile.annual_income == 72000.0
        assert len(records) == 1

    def test_multiple_documents_produce_one_combined_profile(self, test_db):
        citizen = _create_citizen(test_db)
        service = ProfileEnrichmentService(test_db)

        service.enrich_many(
            citizen.id,
            [
                _aadhaar(),
                _mapped(
                    DocumentTypeEnum.INCOME_CERTIFICATE,
                    profile_updates={"annual_income": 72000.0},
                ),
                _mapped(
                    DocumentTypeEnum.CASTE_CERTIFICATE,
                    profile_updates={"caste": "Vanniyar"},
                ),
            ],
        )

        refreshed = CitizenRepository(test_db).get_by_id(citizen.id)
        profile = CitizenProfileRepository(test_db).get_by_citizen_id(citizen.id)
        assert refreshed.full_name == "Selvam Murugan"
        assert profile.annual_income == 72000.0
        assert profile.caste == "Vanniyar"


# ── Null handling ─────────────────────────────────────────────────────────────

class TestNullHandling:
    def test_null_values_do_not_overwrite_existing_values(self, test_db):
        citizen = _create_citizen(test_db)
        service = ProfileEnrichmentService(test_db)

        # First set income.
        service.enrich(
            citizen.id,
            _mapped(
                DocumentTypeEnum.INCOME_CERTIFICATE,
                profile_updates={"annual_income": 72000.0},
            ),
        )
        # Second document supplies None for annual_income.
        service.enrich(
            citizen.id,
            _mapped(
                DocumentTypeEnum.INCOME_CERTIFICATE,
                profile_updates={"annual_income": None},
            ),
        )

        profile = CitizenProfileRepository(test_db).get_by_citizen_id(citizen.id)
        # Existing value preserved.
        assert profile.annual_income == 72000.0


# ── Land records ──────────────────────────────────────────────────────────────

class TestLandRecords:
    def test_multiple_land_parcels_are_preserved(self, test_db):
        citizen = _create_citizen(test_db)
        service = ProfileEnrichmentService(test_db)

        service.enrich(
            citizen.id,
            _mapped(
                DocumentTypeEnum.LAND_RECORD,
                land_updates=[
                    _land("123/2A", land_area=2.5, land_area_unit="acres"),
                    _land("456/1B", land_area=1.0, land_area_unit="acres"),
                ],
            ),
        )

        records = LandRecordRepository(test_db).get_by_citizen_id(citizen.id)
        surveys = {r.survey_number for r in records}
        assert surveys == {"123/2A", "456/1B"}
        total = LandRecordRepository(test_db).get_total_area(citizen.id)
        assert total == 3.5

    def test_same_land_record_does_not_create_duplicates(self, test_db):
        citizen = _create_citizen(test_db)
        service = ProfileEnrichmentService(test_db)

        land_doc = _mapped(
            DocumentTypeEnum.LAND_RECORD,
            land_updates=[_land("123/2A", land_area=2.5, land_area_unit="acres")],
        )
        service.enrich(citizen.id, land_doc)
        service.enrich(citizen.id, land_doc)

        records = LandRecordRepository(test_db).get_by_citizen_id(citizen.id)
        assert len(records) == 1
        assert records[0].land_area == 2.5

    def test_existing_land_record_can_be_enriched_with_missing_fields(self, test_db):
        citizen = _create_citizen(test_db)
        service = ProfileEnrichmentService(test_db)

        # First doc: only survey + area.
        service.enrich(
            citizen.id,
            _mapped(
                DocumentTypeEnum.LAND_RECORD,
                land_updates=[_land("123/2A", land_area=2.5)],
            ),
        )
        # Second doc: same survey, adds village + patta.
        service.enrich(
            citizen.id,
            _mapped(
                DocumentTypeEnum.LAND_RECORD,
                land_updates=[
                    _land(
                        "123/2A",
                        land_area=2.5,
                        village="Periyakulam",
                        patta_number="TN-001",
                    )
                ],
            ),
        )

        records = LandRecordRepository(test_db).get_by_citizen_id(citizen.id)
        assert len(records) == 1
        assert records[0].village == "Periyakulam"
        assert records[0].patta_number == "TN-001"
        assert records[0].land_area == 2.5


# ── Farmer rules ──────────────────────────────────────────────────────────────

class TestFarmerRules:
    def test_farmer_id_sets_farmer_status(self, test_db):
        citizen = _create_citizen(test_db)
        service = ProfileEnrichmentService(test_db)

        service.enrich(
            citizen.id,
            _mapped(
                DocumentTypeEnum.FARMER_ID,
                profile_updates={"is_farmer": True, "occupation": "Farmer"},
            ),
        )

        profile = CitizenProfileRepository(test_db).get_by_citizen_id(citizen.id)
        assert profile.is_farmer is True
        assert profile.occupation == "Farmer"

    def test_land_ownership_alone_does_not_set_farmer_status(self, test_db):
        citizen = _create_citizen(test_db)
        # A profile already exists (e.g. created by an earlier non-farmer
        # document); land alone must NOT flip is_farmer to true.
        CitizenProfileRepository(test_db).upsert(citizen.id, {"is_farmer": False})
        service = ProfileEnrichmentService(test_db)

        service.enrich(
            citizen.id,
            _mapped(
                DocumentTypeEnum.LAND_RECORD,
                land_updates=[_land("123/2A", land_area=2.5, land_area_unit="acres")],
            ),
        )

        profile = CitizenProfileRepository(test_db).get_by_citizen_id(citizen.id)
        # Land ownership alone must NOT imply farmer status.
        assert profile is not None
        assert profile.is_farmer is False


# ── Idempotency ───────────────────────────────────────────────────────────────

class TestIdempotency:
    def test_processing_same_aadhaar_twice_is_safe(self, test_db):
        citizen = _create_citizen(test_db)
        service = ProfileEnrichmentService(test_db)

        service.enrich(citizen.id, _aadhaar())
        service.enrich(citizen.id, _aadhaar())

        refreshed = CitizenRepository(test_db).get_by_id(citizen.id)
        assert refreshed.full_name == "Selvam Murugan"
        # No duplicate profile.
        repo = CitizenProfileRepository(test_db)
        assert repo.get_by_citizen_id(citizen.id) is not None

    def test_processing_same_land_document_twice_is_safe(self, test_db):
        citizen = _create_citizen(test_db)
        service = ProfileEnrichmentService(test_db)

        service.enrich(
            citizen.id,
            _mapped(
                DocumentTypeEnum.LAND_RECORD,
                land_updates=[_land("123/2A", land_area=2.5)],
            ),
        )
        service.enrich(
            citizen.id,
            _mapped(
                DocumentTypeEnum.LAND_RECORD,
                land_updates=[_land("123/2A", land_area=2.5)],
            ),
        )

        records = LandRecordRepository(test_db).get_by_citizen_id(citizen.id)
        assert len(records) == 1

    def test_processing_same_set_of_documents_twice_is_safe(self, test_db):
        citizen = _create_citizen(test_db)
        service = ProfileEnrichmentService(test_db)

        docs = [
            _aadhaar(),
            _mapped(
                DocumentTypeEnum.LAND_RECORD,
                land_updates=[_land("123/2A", land_area=2.5)],
            ),
        ]
        service.enrich_many(citizen.id, docs)
        service.enrich_many(citizen.id, docs)

        records = LandRecordRepository(test_db).get_by_citizen_id(citizen.id)
        assert len(records) == 1
        assert CitizenRepository(test_db).get_by_id(citizen.id).full_name == "Selvam Murugan"


# ── Completion ────────────────────────────────────────────────────────────────

class TestCompletion:
    def test_completion_increases_after_enrichment(self, test_db):
        citizen = _create_citizen(test_db)
        # Minimal profile (no enriched fields yet).
        CitizenProfileRepository(test_db).upsert(citizen.id, {})
        baseline = CitizenProfileRepository(test_db).get_by_citizen_id(citizen.id)
        baseline_completion = baseline.profile_completion_percentage

        service = ProfileEnrichmentService(test_db)
        result = service.enrich(citizen.id, _aadhaar())

        assert result.profile_completion_percentage >= 0
        profile = CitizenProfileRepository(test_db).get_by_citizen_id(citizen.id)
        assert profile.profile_completion_percentage == result.profile_completion_percentage


# ── Conflicts ─────────────────────────────────────────────────────────────────

class TestConflicts:
    def test_conflicting_values_are_deterministic_and_reported(self, test_db):
        citizen = _create_citizen(test_db)
        service = ProfileEnrichmentService(test_db)

        result = service.enrich_many(
            citizen.id,
            [
                _mapped(
                    DocumentTypeEnum.INCOME_CERTIFICATE,
                    profile_updates={"annual_income": 72000.0},
                    doc_id="doc-income-a",
                ),
                _mapped(
                    DocumentTypeEnum.INCOME_CERTIFICATE,
                    profile_updates={"annual_income": 85000.0},
                    doc_id="doc-income-b",
                ),
            ],
        )

        profile = CitizenProfileRepository(test_db).get_by_citizen_id(citizen.id)
        # First non-null in input order is retained.
        assert profile.annual_income == 72000.0
        # Conflict is reported, not hidden.
        assert len(result.conflicts) == 1
        conflict = result.conflicts[0]
        assert conflict.field == "annual_income"
        assert conflict.retained_value == 72000.0
        assert conflict.conflicting_value == 85000.0


# ── Transaction / error handling ──────────────────────────────────────────────

class TestTransactionErrorHandling:
    def test_citizen_not_found_raises_before_any_write(self, test_db):
        service = ProfileEnrichmentService(test_db)

        with pytest.raises(NotFoundError):
            service.enrich("does-not-exist", _aadhaar())


# ── Result reporting ──────────────────────────────────────────────────────────

class TestResultReporting:
    def test_enrichment_result_reports_outcome(self, test_db):
        citizen = _create_citizen(test_db)
        service = ProfileEnrichmentService(test_db)

        result = service.enrich_many(
            citizen.id,
            [
                _aadhaar(),
                _mapped(
                    DocumentTypeEnum.INCOME_CERTIFICATE,
                    profile_updates={"annual_income": 72000.0},
                ),
                _mapped(
                    DocumentTypeEnum.LAND_RECORD,
                    land_updates=[_land("123/2A", land_area=2.5)],
                ),
            ],
        )

        assert isinstance(result, EnrichmentResult)
        assert result.citizen_id == citizen.id
        assert result.processed_documents == 3
        assert "full_name" in result.updated_citizen_fields
        assert "annual_income" in result.updated_profile_fields
        assert result.created_land_records == ["123/2A"]
        assert result.profile_completion_percentage >= 0


# ── End-to-end multi-document scenario ───────────────────────────────────────

class TestEndToEndScenario:
    def test_multiple_documents_construct_one_coherent_citizen_state(self, test_db):
        """Aadhaar + Land1 + Land2 + Income + Caste → one coherent profile.

        Proves that multiple documents can construct a single citizen state:
        2.5 + 1.0 = 3.5 acres via existing land-record aggregation (never
        hardcoded into the profile).
        """
        citizen = _create_citizen(test_db)
        service = ProfileEnrichmentService(test_db)

        result = service.enrich_many(
            citizen.id,
            [
                _aadhaar(),
                _mapped(
                    DocumentTypeEnum.LAND_RECORD,
                    land_updates=[
                        _land(
                            "123/2A",
                            land_area=2.5,
                            land_area_unit="acres",
                            land_type="agricultural",
                        )
                    ],
                ),
                _mapped(
                    DocumentTypeEnum.LAND_RECORD,
                    land_updates=[
                        _land(
                            "456/1B",
                            land_area=1.0,
                            land_area_unit="acres",
                            land_type="agricultural",
                        )
                    ],
                ),
                _mapped(
                    DocumentTypeEnum.INCOME_CERTIFICATE,
                    profile_updates={
                        "annual_income": 72000.0,
                        "income_category": "bpl",
                    },
                ),
                _mapped(
                    DocumentTypeEnum.CASTE_CERTIFICATE,
                    profile_updates={
                        "caste": "Vanniyar",
                        "community": "MBC",
                        "sub_caste": "Padayachi",
                    },
                ),
            ],
        )

        # Citizen (from Aadhaar).
        refreshed = CitizenRepository(test_db).get_by_id(citizen.id)
        assert refreshed.full_name == "Selvam Murugan"
        assert refreshed.district == "Villupuram"

        # Profile (income + caste).
        profile = CitizenProfileRepository(test_db).get_by_citizen_id(citizen.id)
        assert profile.annual_income == 72000.0
        assert profile.income_category == "bpl"
        assert profile.caste == "Vanniyar"
        assert profile.community == "MBC"
        assert profile.sub_caste == "Padayachi"

        # Land records preserved separately.
        records = LandRecordRepository(test_db).get_by_citizen_id(citizen.id)
        surveys = {r.survey_number: r.land_area for r in records}
        assert surveys == {"123/2A": 2.5, "456/1B": 1.0}

        # Total land area via existing aggregation == 3.5 (not hardcoded).
        total = LandRecordRepository(test_db).get_total_area(citizen.id)
        assert total == 3.5

        # Result sanitization.
        assert result.processed_documents == 5
        assert len(result.created_land_records) == 2
        assert result.profile_completion_percentage >= 0
