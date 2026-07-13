"""Service Layer — DigiLocker Sync & Document Management (Module 2)"""
from datetime import datetime
from typing import Dict, Any
from uuid import uuid4
from sqlalchemy.orm import Session

from app.repositories.citizen_repository import CitizenRepository
from app.repositories.citizen_profile_repository import CitizenProfileRepository, LandRecordRepository
from app.repositories.digilocker_repository import DigiLockerRepository, GovernmentDocumentRepository
from app.models.citizen_profile import ProfileSyncStatus
from app.utils.mock_digilocker_data import (
    get_mock_profile,
    get_mock_land_records,
    get_mock_documents,
)
from app.exceptions.exceptions import (
    NotFoundError,
    SyncFailedError,
    DigiLockerUnavailableError,
    ProfileNotFoundError,
    DocumentNotFoundError,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class DigiLockerService:
    """Handles DigiLocker sync, document retrieval, and status checks"""

    def __init__(self, db: Session):
        self.db = db
        self.citizen_repo = CitizenRepository(db)
        self.profile_repo = CitizenProfileRepository(db)
        self.land_repo = LandRecordRepository(db)
        self.digilocker_repo = DigiLockerRepository(db)
        self.doc_repo = GovernmentDocumentRepository(db)

    def sync(self, citizen_id: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Perform DigiLocker sync for a citizen.
        Creates or updates profile, land records, and government documents.
        """
        citizen = self.citizen_repo.get_by_id(citizen_id)
        if not citizen:
            raise NotFoundError("Citizen not found", resource="citizen")

        # Check if already synced and force_refresh is False
        existing_digilocker = self.digilocker_repo.get_by_citizen_id(citizen_id)
        if existing_digilocker and existing_digilocker.last_sync_at and not force_refresh:
            logger.info(f"DigiLocker already synced for citizen: {citizen_id}, skipping")
            doc_counts = self.doc_repo.count_by_citizen_id(citizen_id)
            return {
                "citizen_id": citizen_id,
                "sync_status": "synced",
                "documents_synced": doc_counts["total"],
                "profile_updated": False,
                "message": "Already synced. Use force_refresh=true to re-sync.",
            }

        logger.info(f"Starting DigiLocker sync for citizen: {citizen_id}")

        try:
            # Step 1: Upsert DigiLocker master record
            digilocker_id = f"DL-{citizen_id[:8].upper()}-{str(uuid4())[:4].upper()}"
            sync_count = "1"
            if existing_digilocker:
                try:
                    sync_count = str(int(existing_digilocker.sync_count or "0") + 1)
                except (ValueError, TypeError):
                    sync_count = "1"

            digilocker_record = self.digilocker_repo.upsert(
                citizen_id,
                {
                    "digilocker_id": existing_digilocker.digilocker_id if existing_digilocker else digilocker_id,
                    "is_active": True,
                    "last_sync_at": datetime.utcnow(),
                    "sync_count": sync_count,
                },
            )

            # Step 2: Fetch mock profile data
            mock_profile = get_mock_profile(citizen.aadhaar_number, citizen.smart_ration_card)

            # Step 3: Calculate profile completion
            completion = self._calculate_completion(citizen, mock_profile)

            # Step 4: Upsert citizen profile
            profile_data = {**mock_profile} if mock_profile else {}
            profile_data["profile_completion_percentage"] = completion
            profile_data["sync_status"] = ProfileSyncStatus.SYNCED.value
            profile_data["last_synced_at"] = datetime.utcnow()

            self.profile_repo.upsert(citizen_id, profile_data)

            # Step 5: Sync land records (delete old, insert new)
            self.land_repo.delete_by_citizen_id(citizen_id)
            mock_land = get_mock_land_records(citizen.aadhaar_number, citizen.smart_ration_card)
            for land_data in mock_land:
                land_data["citizen_id"] = citizen_id
                self.land_repo.create(land_data)

            # Step 6: Sync documents (soft-delete old, insert new)
            self.doc_repo.delete_by_citizen_id(citizen_id)
            mock_docs = get_mock_documents(
                citizen_id=citizen_id,
                digilocker_record_id=digilocker_record.id,
                aadhaar=citizen.aadhaar_number,
                ration_card=citizen.smart_ration_card,
                full_name=citizen.full_name,
            )
            self.doc_repo.bulk_create(mock_docs)

            # Step 7: Update citizen's digilocker_sync_at
            self.citizen_repo.update(citizen_id, {"digilocker_sync_at": datetime.utcnow()})

            logger.info(
                f"DigiLocker sync completed for citizen: {citizen_id} — "
                f"{len(mock_docs)} documents, {len(mock_land)} land records"
            )

            return {
                "citizen_id": citizen_id,
                "sync_status": "synced",
                "documents_synced": len(mock_docs),
                "profile_updated": True,
                "message": "DigiLocker sync completed successfully",
            }

        except (NotFoundError, SyncFailedError):
            raise
        except Exception as e:
            logger.error(f"DigiLocker sync failed for citizen {citizen_id}: {str(e)}")
            # Mark profile sync as failed
            try:
                self.profile_repo.upsert(
                    citizen_id,
                    {"sync_status": ProfileSyncStatus.SYNC_FAILED.value},
                )
            except Exception:
                pass
            raise SyncFailedError(f"DigiLocker sync failed: {str(e)}")

    def get_status(self, citizen_id: str) -> Dict[str, Any]:
        """Get DigiLocker sync status for a citizen"""
        citizen = self.citizen_repo.get_by_id(citizen_id)
        if not citizen:
            raise NotFoundError("Citizen not found", resource="citizen")

        digilocker_record = self.digilocker_repo.get_by_citizen_id(citizen_id)
        doc_counts = self.doc_repo.count_by_citizen_id(citizen_id)

        return {
            "citizen_id": citizen_id,
            "digilocker_id": digilocker_record.digilocker_id if digilocker_record else None,
            "is_active": digilocker_record.is_active if digilocker_record else False,
            "last_sync_at": digilocker_record.last_sync_at if digilocker_record else None,
            "sync_count": digilocker_record.sync_count if digilocker_record else "0",
            "total_documents": doc_counts["total"],
            "verified_documents": doc_counts["verified"],
            "pending_documents": doc_counts["pending"],
            "expired_documents": doc_counts["expired"],
        }

    def get_documents(self, citizen_id: str) -> list:
        """Get all government documents for a citizen"""
        citizen = self.citizen_repo.get_by_id(citizen_id)
        if not citizen:
            raise NotFoundError("Citizen not found", resource="citizen")

        return self.doc_repo.get_by_citizen_id(citizen_id)

    def get_document_by_id(self, citizen_id: str, document_id: str):
        """Get a specific document by ID, ensuring it belongs to the citizen"""
        doc = self.doc_repo.get_by_id(document_id)
        if not doc or doc.citizen_id != citizen_id:
            raise DocumentNotFoundError(document_id)
        return doc

    def _calculate_completion(self, citizen, mock_profile: dict) -> int:
        """Calculate profile completion percentage"""
        fields = [
            citizen.full_name,
            citizen.email,
            citizen.phone,
            citizen.gender,
            citizen.date_of_birth,
            citizen.aadhaar_number,
            citizen.smart_ration_card,
            citizen.district,
            citizen.state,
            citizen.village,
            citizen.pincode,
            mock_profile.get("father_name") if mock_profile else None,
            mock_profile.get("occupation") if mock_profile else None,
            mock_profile.get("annual_income") if mock_profile else None,
            mock_profile.get("caste") if mock_profile else None,
            mock_profile.get("religion") if mock_profile else None,
            mock_profile.get("education_level") if mock_profile else None,
            mock_profile.get("blood_group") if mock_profile else None,
            mock_profile.get("marital_status") if mock_profile else None,
            mock_profile.get("family_member_count") if mock_profile else None,
        ]
        filled = sum(1 for f in fields if f is not None and f != "")
        return int((filled / len(fields)) * 100)
