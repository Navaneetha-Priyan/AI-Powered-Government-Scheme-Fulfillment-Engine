"""Repository Layer - Data Access for DigiLocker & Government Documents (Module 2)"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.digilocker import DigiLockerRecord, GovernmentDocument, DocumentType
from app.exceptions.exceptions import DatabaseError, DocumentNotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)


class DigiLockerRepository:
    """Repository for DigiLockerRecord data operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, record_data: dict) -> DigiLockerRecord:
        """Create a DigiLocker record"""
        try:
            record = DigiLockerRecord(**record_data)
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            logger.info(f"DigiLockerRecord created for citizen: {record_data.get('citizen_id')}")
            return record
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating DigiLocker record: {str(e)}")
            raise DatabaseError(f"Failed to create DigiLocker record: {str(e)}")

    def get_by_citizen_id(self, citizen_id: str) -> Optional[DigiLockerRecord]:
        """Get DigiLocker record by citizen ID"""
        try:
            return (
                self.db.query(DigiLockerRecord)
                .filter(DigiLockerRecord.citizen_id == citizen_id)
                .first()
            )
        except Exception as e:
            logger.error(f"Error fetching DigiLocker record: {str(e)}")
            raise DatabaseError(f"Failed to fetch DigiLocker record: {str(e)}")

    def get_by_digilocker_id(self, digilocker_id: str) -> Optional[DigiLockerRecord]:
        """Get DigiLocker record by DigiLocker ID"""
        try:
            return (
                self.db.query(DigiLockerRecord)
                .filter(DigiLockerRecord.digilocker_id == digilocker_id)
                .first()
            )
        except Exception as e:
            logger.error(f"Error fetching DigiLocker record by id: {str(e)}")
            raise DatabaseError(f"Failed to fetch DigiLocker record: {str(e)}")

    def update(self, citizen_id: str, update_data: dict) -> DigiLockerRecord:
        """Update DigiLocker record"""
        try:
            record = self.get_by_citizen_id(citizen_id)
            if not record:
                raise DatabaseError("DigiLocker record not found")

            for key, value in update_data.items():
                if hasattr(record, key):
                    setattr(record, key, value)

            self.db.commit()
            self.db.refresh(record)
            logger.info(f"DigiLockerRecord updated for citizen: {citizen_id}")
            return record
        except DatabaseError:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating DigiLocker record: {str(e)}")
            raise DatabaseError(f"Failed to update DigiLocker record: {str(e)}")

    def upsert(self, citizen_id: str, record_data: dict) -> DigiLockerRecord:
        """Create or update DigiLocker record"""
        existing = self.get_by_citizen_id(citizen_id)
        if existing:
            return self.update(citizen_id, record_data)
        record_data["citizen_id"] = citizen_id
        return self.create(record_data)

    def exists(self, citizen_id: str) -> bool:
        """Check if DigiLocker record exists"""
        try:
            return (
                self.db.query(DigiLockerRecord)
                .filter(DigiLockerRecord.citizen_id == citizen_id)
                .first()
                is not None
            )
        except Exception as e:
            logger.error(f"Error checking DigiLocker existence: {str(e)}")
            raise DatabaseError(f"Failed to check DigiLocker record: {str(e)}")


class GovernmentDocumentRepository:
    """Repository for GovernmentDocument data operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, doc_data: dict) -> GovernmentDocument:
        """Create a government document"""
        try:
            doc = GovernmentDocument(**doc_data)
            self.db.add(doc)
            self.db.commit()
            self.db.refresh(doc)
            logger.info(f"GovernmentDocument created: {doc_data.get('document_type')} for citizen: {doc_data.get('citizen_id')}")
            return doc
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating government document: {str(e)}")
            raise DatabaseError(f"Failed to create government document: {str(e)}")

    def bulk_create(self, docs: List[dict]) -> List[GovernmentDocument]:
        """Bulk create government documents"""
        try:
            created = []
            for doc_data in docs:
                doc = GovernmentDocument(**doc_data)
                self.db.add(doc)
                created.append(doc)
            self.db.commit()
            for doc in created:
                self.db.refresh(doc)
            logger.info(f"Bulk created {len(created)} government documents")
            return created
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error bulk creating documents: {str(e)}")
            raise DatabaseError(f"Failed to bulk create documents: {str(e)}")

    def get_by_citizen_id(
        self, citizen_id: str, active_only: bool = True
    ) -> List[GovernmentDocument]:
        """Get all documents for a citizen"""
        try:
            query = self.db.query(GovernmentDocument).filter(
                GovernmentDocument.citizen_id == citizen_id
            )
            if active_only:
                query = query.filter(GovernmentDocument.is_active == True)
            return query.order_by(GovernmentDocument.document_type).all()
        except Exception as e:
            logger.error(f"Error fetching documents: {str(e)}")
            raise DatabaseError(f"Failed to fetch documents: {str(e)}")

    def get_by_id(self, doc_id: str) -> Optional[GovernmentDocument]:
        """Get document by ID"""
        try:
            return (
                self.db.query(GovernmentDocument)
                .filter(
                    and_(
                        GovernmentDocument.id == doc_id,
                        GovernmentDocument.is_active == True,
                    )
                )
                .first()
            )
        except Exception as e:
            logger.error(f"Error fetching document by id: {str(e)}")
            raise DatabaseError(f"Failed to fetch document: {str(e)}")

    def get_by_type(
        self, citizen_id: str, document_type: DocumentType
    ) -> Optional[GovernmentDocument]:
        """Get document by type for a citizen"""
        try:
            return (
                self.db.query(GovernmentDocument)
                .filter(
                    and_(
                        GovernmentDocument.citizen_id == citizen_id,
                        GovernmentDocument.document_type == document_type,
                        GovernmentDocument.is_active == True,
                    )
                )
                .first()
            )
        except Exception as e:
            logger.error(f"Error fetching document by type: {str(e)}")
            raise DatabaseError(f"Failed to fetch document: {str(e)}")

    def delete_by_citizen_id(self, citizen_id: str) -> int:
        """Soft-delete all documents for a citizen (used during re-sync)"""
        try:
            count = (
                self.db.query(GovernmentDocument)
                .filter(GovernmentDocument.citizen_id == citizen_id)
                .update({"is_active": False})
            )
            self.db.commit()
            logger.info(f"Soft-deleted {count} documents for citizen: {citizen_id}")
            return count
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting documents: {str(e)}")
            raise DatabaseError(f"Failed to delete documents: {str(e)}")

    def count_by_citizen_id(self, citizen_id: str) -> dict:
        """Count documents by verification status"""
        try:
            docs = self.get_by_citizen_id(citizen_id)
            from app.models.digilocker import DocumentVerificationStatus
            return {
                "total": len(docs),
                "verified": sum(1 for d in docs if d.verification_status == DocumentVerificationStatus.VERIFIED),
                "pending": sum(1 for d in docs if d.verification_status == DocumentVerificationStatus.PENDING),
                "expired": sum(1 for d in docs if d.verification_status == DocumentVerificationStatus.EXPIRED),
            }
        except Exception as e:
            logger.error(f"Error counting documents: {str(e)}")
            return {"total": 0, "verified": 0, "pending": 0, "expired": 0}
