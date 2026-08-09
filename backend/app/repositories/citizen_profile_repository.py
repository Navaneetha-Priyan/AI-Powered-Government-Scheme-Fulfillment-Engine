"""Repository Layer - Data Access for Citizen Profile & Land Records (Module 2)"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.citizen_profile import CitizenProfile, LandRecord, ProfileSyncStatus
from app.exceptions.exceptions import DatabaseError, ProfileNotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)


class CitizenProfileRepository:
    """Repository for CitizenProfile data operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, profile_data: dict) -> CitizenProfile:
        """Create a new citizen profile"""
        try:
            profile = CitizenProfile(**profile_data)
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)
            logger.info(f"CitizenProfile created for citizen: {profile_data.get('citizen_id')}")
            return profile
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating citizen profile: {str(e)}")
            raise DatabaseError(f"Failed to create citizen profile: {str(e)}")

    def get_by_citizen_id(self, citizen_id: str) -> Optional[CitizenProfile]:
        """Get profile by citizen ID"""
        try:
            return (
                self.db.query(CitizenProfile)
                .filter(CitizenProfile.citizen_id == citizen_id)
                .first()
            )
        except Exception as e:
            logger.error(f"Error fetching citizen profile: {str(e)}")
            raise DatabaseError(f"Failed to fetch citizen profile: {str(e)}")

    def get_by_id(self, profile_id: str) -> Optional[CitizenProfile]:
        """Get profile by profile ID"""
        try:
            return (
                self.db.query(CitizenProfile)
                .filter(CitizenProfile.id == profile_id)
                .first()
            )
        except Exception as e:
            logger.error(f"Error fetching citizen profile by id: {str(e)}")
            raise DatabaseError(f"Failed to fetch citizen profile: {str(e)}")

    def update(self, citizen_id: str, update_data: dict) -> CitizenProfile:
        """Update citizen profile"""
        try:
            profile = self.get_by_citizen_id(citizen_id)
            if not profile:
                raise ProfileNotFoundError(citizen_id)

            for key, value in update_data.items():
                if value is not None and hasattr(profile, key):
                    setattr(profile, key, value)

            self.db.commit()
            self.db.refresh(profile)
            logger.info(f"CitizenProfile updated for citizen: {citizen_id}")
            return profile
        except ProfileNotFoundError:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating citizen profile: {str(e)}")
            raise DatabaseError(f"Failed to update citizen profile: {str(e)}")

    def upsert(self, citizen_id: str, profile_data: dict) -> CitizenProfile:
        """Create or update citizen profile"""
        existing = self.get_by_citizen_id(citizen_id)
        if existing:
            return self.update(citizen_id, profile_data)
        profile_data["citizen_id"] = citizen_id
        return self.create(profile_data)

    def exists(self, citizen_id: str) -> bool:
        """Check if profile exists for citizen"""
        try:
            return (
                self.db.query(CitizenProfile)
                .filter(CitizenProfile.citizen_id == citizen_id)
                .first()
                is not None
            )
        except Exception as e:
            logger.error(f"Error checking profile existence: {str(e)}")
            raise DatabaseError(f"Failed to check profile: {str(e)}")


class LandRecordRepository:
    """Repository for LandRecord data operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, record_data: dict) -> LandRecord:
        """Create a land record"""
        try:
            record = LandRecord(**record_data)
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            logger.info(f"LandRecord created for citizen: {record_data.get('citizen_id')}")
            return record
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating land record: {str(e)}")
            raise DatabaseError(f"Failed to create land record: {str(e)}")

    def get_by_citizen_id(self, citizen_id: str) -> List[LandRecord]:
        """Get all land records for a citizen"""
        try:
            return (
                self.db.query(LandRecord)
                .filter(LandRecord.citizen_id == citizen_id)
                .all()
            )
        except Exception as e:
            logger.error(f"Error fetching land records: {str(e)}")
            raise DatabaseError(f"Failed to fetch land records: {str(e)}")

    def get_by_id(self, record_id: str) -> Optional[LandRecord]:
        """Get land record by ID"""
        try:
            return (
                self.db.query(LandRecord)
                .filter(LandRecord.id == record_id)
                .first()
            )
        except Exception as e:
            logger.error(f"Error fetching land record: {str(e)}")
            raise DatabaseError(f"Failed to fetch land record: {str(e)}")

    def get_by_citizen_and_survey(
        self, citizen_id: str, survey_number: str
    ) -> Optional[LandRecord]:
        """Find an existing land record for a citizen by survey number.

        Used by :class:`ProfileEnrichmentService` to achieve idempotency: when
        the same land document is processed more than once, the survey number
        (the strongest available existing identifier) lets us update the
        existing record instead of inserting a duplicate.
        """
        try:
            return (
                self.db.query(LandRecord)
                .filter(
                    and_(
                        LandRecord.citizen_id == citizen_id,
                        LandRecord.survey_number == survey_number,
                    )
                )
                .first()
            )
        except Exception as e:
            logger.error(f"Error fetching land record by survey: {str(e)}")
            raise DatabaseError(f"Failed to fetch land record by survey: {str(e)}")

    def delete_by_citizen_id(self, citizen_id: str) -> int:
        """Delete all land records for a citizen (used during re-sync)"""
        try:
            count = (
                self.db.query(LandRecord)
                .filter(LandRecord.citizen_id == citizen_id)
                .delete()
            )
            self.db.commit()
            logger.info(f"Deleted {count} land records for citizen: {citizen_id}")
            return count
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting land records: {str(e)}")
            raise DatabaseError(f"Failed to delete land records: {str(e)}")

    def get_total_area(self, citizen_id: str) -> float:
        """Get total land area for a citizen"""
        try:
            records = self.get_by_citizen_id(citizen_id)
            return sum(r.land_area or 0.0 for r in records)
        except Exception as e:
            logger.error(f"Error calculating total land area: {str(e)}")
            return 0.0
