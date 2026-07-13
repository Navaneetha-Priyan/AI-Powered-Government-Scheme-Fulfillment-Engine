"""Service Layer — Citizen Profile Management (Module 2)"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.repositories.citizen_repository import CitizenRepository
from app.repositories.citizen_profile_repository import CitizenProfileRepository, LandRecordRepository
from app.repositories.digilocker_repository import DigiLockerRepository, GovernmentDocumentRepository
from app.schemas.citizen_profile import CitizenProfileUpdateRequest
from app.exceptions.exceptions import NotFoundError, ProfileNotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)


class CitizenProfileService:
    """Handles citizen profile retrieval, update, and dashboard assembly"""

    def __init__(self, db: Session):
        self.db = db
        self.citizen_repo = CitizenRepository(db)
        self.profile_repo = CitizenProfileRepository(db)
        self.land_repo = LandRecordRepository(db)
        self.digilocker_repo = DigiLockerRepository(db)
        self.doc_repo = GovernmentDocumentRepository(db)

    def get_profile(self, citizen_id: str) -> Dict[str, Any]:
        """Get extended citizen profile"""
        citizen = self.citizen_repo.get_by_id(citizen_id)
        if not citizen:
            raise NotFoundError("Citizen not found", resource="citizen")

        profile = self.profile_repo.get_by_citizen_id(citizen_id)
        if not profile:
            raise ProfileNotFoundError(citizen_id)

        logger.info(f"Profile retrieved for citizen: {citizen_id}")
        return profile

    def get_full_profile(self, citizen_id: str) -> Dict[str, Any]:
        """Get combined auth + extended profile details"""
        citizen = self.citizen_repo.get_by_id(citizen_id)
        if not citizen:
            raise NotFoundError("Citizen not found", resource="citizen")

        profile = self.profile_repo.get_by_citizen_id(citizen_id)
        logger.info(f"Full profile details retrieved for citizen: {citizen_id}")
        return {"citizen": citizen, "profile": profile}

    def update_profile(self, citizen_id: str, update_data: CitizenProfileUpdateRequest) -> Any:
        """Update extended citizen profile"""
        citizen = self.citizen_repo.get_by_id(citizen_id)
        if not citizen:
            raise NotFoundError("Citizen not found", resource="citizen")

        update_dict = update_data.model_dump(exclude_unset=True)

        # Recalculate completion after update
        profile = self.profile_repo.upsert(citizen_id, update_dict)

        logger.info(f"Profile updated for citizen: {citizen_id}")
        return profile

    def get_dashboard(self, citizen_id: str) -> Dict[str, Any]:
        """Assemble full citizen dashboard data"""
        citizen = self.citizen_repo.get_by_id(citizen_id)
        if not citizen:
            raise NotFoundError("Citizen not found", resource="citizen")

        profile = self.profile_repo.get_by_citizen_id(citizen_id)
        land_records = self.land_repo.get_by_citizen_id(citizen_id)
        total_land_area = self.land_repo.get_total_area(citizen_id)
        doc_counts = self.doc_repo.count_by_citizen_id(citizen_id)
        digilocker = self.digilocker_repo.get_by_citizen_id(citizen_id)

        completion = profile.profile_completion_percentage if profile else 0

        logger.info(f"Dashboard assembled for citizen: {citizen_id}")
        return {
            "citizen_id": citizen.id,
            "full_name": citizen.full_name,
            "email": citizen.email,
            "phone": citizen.phone,
            "gender": citizen.gender,
            "date_of_birth": citizen.date_of_birth,
            "profile_photo_url": citizen.profile_photo_url,
            "aadhaar_number": citizen.aadhaar_number,
            "smart_ration_card": citizen.smart_ration_card,
            "address_line1": citizen.address_line1,
            "address_line2": citizen.address_line2,
            "village": citizen.village,
            "taluk": citizen.taluk,
            "district": citizen.district,
            "state": citizen.state,
            "pincode": citizen.pincode,
            "extended_profile": profile,
            "land_records": land_records,
            "total_land_area": total_land_area,
            "total_documents": doc_counts["total"],
            "verified_documents": doc_counts["verified"],
            "digilocker_synced": digilocker is not None and digilocker.last_sync_at is not None,
            "last_synced_at": digilocker.last_sync_at if digilocker else None,
            "account_active": citizen.account_active,
            "last_login": citizen.last_login,
            "profile_completion_percentage": completion,
        }

    def get_income_details(self, citizen_id: str) -> Dict[str, Any]:
        """Get income and economic classification details"""
        citizen = self.citizen_repo.get_by_id(citizen_id)
        if not citizen:
            raise NotFoundError("Citizen not found", resource="citizen")

        profile = self.profile_repo.get_by_citizen_id(citizen_id)
        if not profile:
            raise ProfileNotFoundError(citizen_id)

        logger.info(f"Income details retrieved for citizen: {citizen_id}")
        return {
            "citizen_id": citizen_id,
            "full_name": citizen.full_name,
            "annual_income": profile.annual_income,
            "income_category": profile.income_category,
            "occupation": profile.occupation,
            "is_farmer": profile.is_farmer,
            "farmer_id": profile.farmer_id,
        }

    def get_caste_details(self, citizen_id: str) -> Dict[str, Any]:
        """Get caste and community classification details"""
        citizen = self.citizen_repo.get_by_id(citizen_id)
        if not citizen:
            raise NotFoundError("Citizen not found", resource="citizen")

        profile = self.profile_repo.get_by_citizen_id(citizen_id)
        if not profile:
            raise ProfileNotFoundError(citizen_id)

        logger.info(f"Caste details retrieved for citizen: {citizen_id}")
        return {
            "citizen_id": citizen_id,
            "full_name": citizen.full_name,
            "caste": profile.caste,
            "community": profile.community,
            "sub_caste": profile.sub_caste,
            "religion": profile.religion,
        }

    def get_land_records(self, citizen_id: str) -> Dict[str, Any]:
        """Get all land records for a citizen"""
        citizen = self.citizen_repo.get_by_id(citizen_id)
        if not citizen:
            raise NotFoundError("Citizen not found", resource="citizen")

        records = self.land_repo.get_by_citizen_id(citizen_id)
        total_area = self.land_repo.get_total_area(citizen_id)

        logger.info(f"Land records retrieved for citizen: {citizen_id} — {len(records)} records")
        return {
            "citizen_id": citizen_id,
            "full_name": citizen.full_name,
            "land_records": records,
            "total_records": len(records),
            "total_land_area": total_area,
            "land_area_unit": "acres",
        }
