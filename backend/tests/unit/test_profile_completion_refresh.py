"""Unit tests for profile-completion refresh on profile updates.

``profile_completion_percentage`` is derived data: it must be recomputed and
persisted on **every** path that writes a field feeding
``calculate_profile_completion``.  Two such paths exist:

1. ``CitizenProfileService.update_profile`` (``PUT /api/citizen/profile``) for
   the extended profile columns (occupation, income, caste, ...).
2. ``AuthenticationService.update_profile`` (``PUT /api/auth/profile``) for the
   citizen columns (full_name, date_of_birth, gender, address, pincode).

The eligibility engine reads the stored value through
``CitizenContext.profile_completion_percentage`` and uses it inside
``_profile_match_percentage``, which feeds both the overall ranking score and
the ``application_ready`` gate — so a stale value silently degrades
recommendation quality.

These tests use the real repositories against the in-memory SQLite session
from ``tests/conftest.py`` — no HTTP, RAG, or LLM involved.
"""
from __future__ import annotations

from datetime import datetime

from app.repositories.citizen_repository import CitizenRepository
from app.repositories.citizen_profile_repository import CitizenProfileRepository
from app.schemas.citizen import CitizenUpdateProfileRequest, GenderEnum
from app.schemas.citizen_profile import CitizenProfileUpdateRequest
from app.services.auth_service import AuthenticationService
from app.services.citizen_profile_service import (
    CitizenProfileService,
    calculate_profile_completion,
)


def _create_citizen(db, **overrides):
    """Create a minimal citizen via the real repository."""
    data = {
        "email": "completion@example.com",
        "phone": "9876543213",
        "password_hash": "hashed",
        "full_name": "Selvam Murugan",
        "district": "Villupuram",
        "state": "Tamil Nadu",
    }
    data.update(overrides)
    return CitizenRepository(db).create(data)


def _full_update_request() -> CitizenProfileUpdateRequest:
    """A manual profile edit filling every profile-side completion field."""
    return CitizenProfileUpdateRequest(
        father_name="Ravi Kumar",
        occupation="Farmer",
        annual_income=72000.0,
        caste="Vanniyar",
        religion="Hindu",
        education_level="10th",
        blood_group="O+",
        marital_status="married",
        family_member_count=4,
    )


class TestProfileCompletionRefresh:
    def test_manual_update_recalculates_completion(self, test_db):
        """A manual profile edit must persist a freshly computed completion."""
        citizen = _create_citizen(test_db)
        service = CitizenProfileService(test_db)

        profile = service.update_profile(citizen.id, _full_update_request())

        refreshed_citizen = CitizenRepository(test_db).get_by_id(citizen.id)
        expected = calculate_profile_completion(refreshed_citizen, profile)
        assert profile.profile_completion_percentage == expected
        assert profile.profile_completion_percentage > 0

    def test_completion_matches_recomputed_value_after_repeated_updates(self, test_db):
        """The stored value stays in sync across successive manual edits."""
        citizen = _create_citizen(test_db)
        service = CitizenProfileService(test_db)

        service.update_profile(citizen.id, _full_update_request())
        profile = service.update_profile(
            citizen.id, CitizenProfileUpdateRequest(occupation="Agricultural labourer")
        )

        refreshed_citizen = CitizenRepository(test_db).get_by_id(citizen.id)
        assert profile.profile_completion_percentage == calculate_profile_completion(
            refreshed_citizen, profile
        )

    def test_dashboard_reports_recalculated_completion(self, test_db):
        """The dashboard surfaces the refreshed completion, not a stale zero."""
        citizen = _create_citizen(test_db)
        service = CitizenProfileService(test_db)
        service.update_profile(citizen.id, _full_update_request())

        dashboard = service.get_dashboard(citizen.id)

        stored = CitizenProfileRepository(test_db).get_by_citizen_id(citizen.id)
        assert dashboard["profile_completion_percentage"] == (
            stored.profile_completion_percentage
        )
        assert dashboard["profile_completion_percentage"] > 0

    def test_manual_update_does_not_trust_client_supplied_completion(self, test_db):
        """Completion is derived, never taken from stored/input values.

        ``CitizenProfileUpdateRequest`` deliberately exposes no completion
        field, so an unrelated edit must still leave a correct derived value
        behind (never a caller-controlled one).
        """
        citizen = _create_citizen(test_db)
        repo = CitizenProfileRepository(test_db)
        repo.upsert(citizen.id, {"profile_completion_percentage": 99})
        service = CitizenProfileService(test_db)

        profile = service.update_profile(
            citizen.id, CitizenProfileUpdateRequest(occupation="Farmer")
        )

        refreshed_citizen = CitizenRepository(test_db).get_by_id(citizen.id)
        assert profile.profile_completion_percentage == calculate_profile_completion(
            refreshed_citizen, repo.get_by_citizen_id(citizen.id)
        )

    def test_completion_increases_when_blank_fields_are_filled(self, test_db):
        """Filling previously empty fields raises the derived completion."""
        citizen = _create_citizen(test_db)
        service = CitizenProfileService(test_db)

        baseline = service.update_profile(
            citizen.id, CitizenProfileUpdateRequest(occupation="Farmer")
        ).profile_completion_percentage

        enriched = service.update_profile(
            citizen.id, _full_update_request()
        ).profile_completion_percentage

        assert enriched > baseline


class TestAuthProfileUpdateRefresh:
    """``PUT /api/auth/profile`` edits citizen columns that feed completion.

    ``AuthenticationService.update_profile`` writes ``full_name``,
    ``date_of_birth``, ``gender``, address and ``pincode`` — all part of
    ``calculate_profile_completion`` — so the stored score must be refreshed
    on that path as well, not only on the extended-profile path.
    """

    def test_auth_update_refreshes_completion(self, test_db):
        citizen = _create_citizen(test_db)
        service = AuthenticationService(test_db)

        service.update_profile(
            citizen.id,
            CitizenUpdateProfileRequest(
                date_of_birth=datetime(1990, 5, 12),
                gender=GenderEnum.MALE,
                village="Kandachipuram",
                pincode="605401",
            ),
        )

        profile = CitizenProfileRepository(test_db).get_by_citizen_id(citizen.id)
        refreshed_citizen = CitizenRepository(test_db).get_by_id(citizen.id)
        assert profile is not None
        assert profile.profile_completion_percentage == calculate_profile_completion(
            refreshed_citizen, profile
        )

    def test_auth_update_completion_matches_extended_profile_path(self, test_db):
        """Both profile write paths must agree on the same derived score."""
        citizen = _create_citizen(test_db)
        AuthenticationService(test_db).update_profile(
            citizen.id,
            CitizenUpdateProfileRequest(gender=GenderEnum.FEMALE),
        )

        CitizenProfileService(test_db).update_profile(
            citizen.id, CitizenProfileUpdateRequest(occupation="Farmer")
        )

        profile = CitizenProfileRepository(test_db).get_by_citizen_id(citizen.id)
        refreshed_citizen = CitizenRepository(test_db).get_by_id(citizen.id)
        assert profile.profile_completion_percentage == calculate_profile_completion(
            refreshed_citizen, profile
        )

    def test_auth_update_never_trusts_a_stale_stored_score(self, test_db):
        citizen = _create_citizen(test_db)
        repo = CitizenProfileRepository(test_db)
        repo.upsert(citizen.id, {"profile_completion_percentage": 100})

        AuthenticationService(test_db).update_profile(
            citizen.id,
            CitizenUpdateProfileRequest(village="Kandachipuram"),
        )

        profile = repo.get_by_citizen_id(citizen.id)
        refreshed_citizen = CitizenRepository(test_db).get_by_id(citizen.id)
        assert profile.profile_completion_percentage == calculate_profile_completion(
            refreshed_citizen, profile
        )
        assert profile.profile_completion_percentage < 100