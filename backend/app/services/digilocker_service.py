"""Service Layer — DigiLocker Sync & Document Management (Module 2)"""
from datetime import datetime
from typing import Dict, Any
from uuid import uuid4
from sqlalchemy.orm import Session

from app.repositories.citizen_repository import CitizenRepository
from app.repositories.citizen_profile_repository import CitizenProfileRepository, LandRecordRepository
from app.repositories.digilocker_repository import DigiLockerRepository, GovernmentDocumentRepository
from app.models.citizen_profile import ProfileSyncStatus
from app.models.digilocker import DocumentType, DocumentVerificationStatus
from app.utils.mock_digilocker_data import get_mock_documents
from app.exceptions.exceptions import (
    NotFoundError,
    SyncFailedError,
    DigiLockerUnavailableError,
    ProfileNotFoundError,
    DocumentNotFoundError,
    DocumentMetadataInvalidError,
    UnsupportedDocumentTypeError,
)
from app.services.document_profile_extractor import DocumentProfileExtractor
from app.services.document_profile_mapper import DocumentProfileMapper
from app.services.profile_enrichment_service import ProfileEnrichmentService
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

            # Step 2: Build mock government documents. These structured
            # documents (with doc_metadata from Step 1) are the sole source for
            # the document → profile enrichment pipeline. The legacy
            # get_mock_profile/get_mock_land_records direct assignment is no
            # longer used for persistence.
            mock_docs = get_mock_documents(
                citizen_id=citizen_id,
                digilocker_record_id=digilocker_record.id,
                aadhaar=citizen.aadhaar_number,
                ration_card=citizen.smart_ration_card,
                full_name=citizen.full_name,
                gender=citizen.gender.value if citizen.gender else None,
                date_of_birth=citizen.date_of_birth.isoformat() if citizen.date_of_birth else None,
                address_line1=citizen.address_line1,
                village=citizen.village,
                taluk=citizen.taluk,
                district=citizen.district,
                state=citizen.state,
                pincode=citizen.pincode,
            )

            # Step 3: Persist the documents so they can be consumed by the
            # canonical pipeline (soft-delete old rows, insert new ones).
            self.doc_repo.delete_by_citizen_id(citizen_id)
            created_docs = self.doc_repo.bulk_create(mock_docs)

            # Step 4: Document → profile enrichment pipeline.
            extractor = DocumentProfileExtractor()
            mapper = DocumentProfileMapper()
            enrichment = ProfileEnrichmentService(self.db)

            extracted = []
            extracted_count = 0
            for doc in created_docs:
                try:
                    extracted.append(extractor.extract(doc))
                    extracted_count += 1
                except (DocumentMetadataInvalidError, UnsupportedDocumentTypeError) as exc:
                    # Controlled, document-level error. Skip this document and
                    # report it rather than silently fabricating data or
                    # crashing the whole sync (existing sync error convention
                    # allows the sync to continue when a single document is
                    # invalid while reporting what happened).
                    logger.warning(
                        f"Skipping document {getattr(doc, 'id', '')} "
                        f"({getattr(doc, 'document_type', '')}): {exc}"
                    )

            mapped = mapper.map_many(extracted)

            # Step 5: Enrich citizen profile + land records. The enrichment
            # service handles land-record deduplication (citizen_id +
            # survey_number) and never creates duplicates on re-sync.
            result = enrichment.enrich_many(citizen_id, mapped)

            # Step 6: Mark profile as synced.
            self.profile_repo.upsert(
                citizen_id,
                {
                    "sync_status": ProfileSyncStatus.SYNCED.value,
                    "last_synced_at": datetime.utcnow(),
                },
            )

            # Step 7: Update citizen's digilocker_sync_at
            self.citizen_repo.update(citizen_id, {"digilocker_sync_at": datetime.utcnow()})

            logger.info(
                f"DigiLocker sync completed for citizen: {citizen_id} — "
                f"{len(mock_docs)} documents, {extracted_count} extracted, "
                f"{len(result.created_land_records)} land created, "
                f"{len(result.updated_land_records)} land updated"
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

    def enrich_document(self, document):
        """Run one created GovernmentDocument through the canonical pipeline.

        Extracts structured ``doc_metadata`` (Step 2), maps it (Step 3), and
        enriches the citizen profile/land records (Step 4). This reuses the
        exact same extractor/mapper/enrichment services as the DigiLocker sync
        — no second implementation is introduced here.

        Returns the ``EnrichmentResult``, or ``None`` when the document has no
        structured metadata that can be extracted (e.g. a raw citizen upload
        without OCR-derived structured fields). Controlled document-level
        extraction errors are logged and skipped rather than fabricating data.
        """
        extractor = DocumentProfileExtractor()
        mapper = DocumentProfileMapper()
        enrichment = ProfileEnrichmentService(self.db)

        try:
            extracted = extractor.extract(document)
        except (DocumentMetadataInvalidError, UnsupportedDocumentTypeError) as exc:
            logger.info(
                f"No structured metadata to enrich for document "
                f"{getattr(document, 'id', '')}: {exc}"
            )
            return None

        mapped = mapper.map(extracted)
        return enrichment.enrich(document.citizen_id, mapped)

    def add_uploaded_document(
        self,
        citizen_id: str,
        document_type: str,
        document_name: str,
        document_number: str | None,
        download_url: str,
        metadata: str | None = None,
    ):
        """Create a citizen-uploaded document entry."""
        citizen = self.citizen_repo.get_by_id(citizen_id)
        if not citizen:
            raise NotFoundError("Citizen not found", resource="citizen")

        digilocker = self.digilocker_repo.get_by_citizen_id(citizen_id)
        if not digilocker:
            digilocker = self.digilocker_repo.create(
                {
                    "citizen_id": citizen_id,
                    "digilocker_id": f"UPLOAD-{citizen_id[:8].upper()}-{str(uuid4())[:4].upper()}",
                    "is_active": True,
                    "last_sync_at": None,
                    "sync_count": "0",
                }
            )

        try:
            normalized_type = DocumentType(document_type)
        except ValueError:
            normalized_type = DocumentType.LAND_RECORD

        return self.doc_repo.create(
            {
                "citizen_id": citizen_id,
                "digilocker_record_id": digilocker.id,
                "document_type": normalized_type,
                "document_number": document_number,
                "document_name": document_name,
                "verification_status": DocumentVerificationStatus.PENDING,
                "download_url": download_url,
                "doc_metadata": metadata,
                "is_active": True,
            }
        )

