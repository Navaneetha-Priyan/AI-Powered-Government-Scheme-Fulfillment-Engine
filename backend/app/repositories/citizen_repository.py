"""Repository Layer - Data Access for Citizens"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.citizen import Citizen, CitizenStatus, LoginAudit
from app.exceptions.exceptions import (
    NotFoundError,
    DatabaseError,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class CitizenRepository:
    """Repository for Citizen data operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, citizen_data: dict) -> Citizen:
        """Create a new citizen"""
        try:
            citizen = Citizen(**citizen_data)
            self.db.add(citizen)
            self.db.commit()
            self.db.refresh(citizen)
            logger.info(f"Citizen created: {citizen.id}")
            return citizen
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating citizen: {str(e)}")
            raise DatabaseError(f"Failed to create citizen: {str(e)}")

    def get_by_id(self, citizen_id: str) -> Optional[Citizen]:
        """Get citizen by ID"""
        try:
            citizen = self.db.query(Citizen).filter(
                and_(Citizen.id == citizen_id, Citizen.is_deleted == False)
            ).first()
            return citizen
        except Exception as e:
            logger.error(f"Error fetching citizen by ID: {str(e)}")
            raise DatabaseError(f"Failed to fetch citizen: {str(e)}")

    def get_by_email(self, email: str) -> Optional[Citizen]:
        """Get citizen by email"""
        try:
            citizen = self.db.query(Citizen).filter(
                and_(Citizen.email == email, Citizen.is_deleted == False)
            ).first()
            return citizen
        except Exception as e:
            logger.error(f"Error fetching citizen by email: {str(e)}")
            raise DatabaseError(f"Failed to fetch citizen: {str(e)}")

    def get_by_phone(self, phone: str) -> Optional[Citizen]:
        """Get citizen by phone"""
        try:
            citizen = self.db.query(Citizen).filter(
                and_(Citizen.phone == phone, Citizen.is_deleted == False)
            ).first()
            return citizen
        except Exception as e:
            logger.error(f"Error fetching citizen by phone: {str(e)}")
            raise DatabaseError(f"Failed to fetch citizen: {str(e)}")

    def get_by_aadhaar(self, aadhaar_number: str) -> Optional[Citizen]:
        """Get citizen by Aadhaar number"""
        try:
            citizen = self.db.query(Citizen).filter(
                and_(
                    Citizen.aadhaar_number == aadhaar_number,
                    Citizen.is_deleted == False,
                )
            ).first()
            return citizen
        except Exception as e:
            logger.error(f"Error fetching citizen by Aadhaar: {str(e)}")
            raise DatabaseError(f"Failed to fetch citizen: {str(e)}")

    def get_by_ration_card(self, ration_card: str) -> Optional[Citizen]:
        """Get citizen by Ration Card number"""
        try:
            citizen = self.db.query(Citizen).filter(
                and_(
                    Citizen.smart_ration_card == ration_card,
                    Citizen.is_deleted == False,
                )
            ).first()
            return citizen
        except Exception as e:
            logger.error(f"Error fetching citizen by Ration Card: {str(e)}")
            raise DatabaseError(f"Failed to fetch citizen: {str(e)}")

    def email_exists(self, email: str, exclude_id: Optional[str] = None) -> bool:
        """Check if email exists"""
        try:
            query = self.db.query(Citizen).filter(
                and_(Citizen.email == email, Citizen.is_deleted == False)
            )
            if exclude_id:
                query = query.filter(Citizen.id != exclude_id)
            return query.first() is not None
        except Exception as e:
            logger.error(f"Error checking email existence: {str(e)}")
            raise DatabaseError(f"Failed to check email: {str(e)}")

    def phone_exists(self, phone: str, exclude_id: Optional[str] = None) -> bool:
        """Check if phone exists"""
        try:
            query = self.db.query(Citizen).filter(
                and_(Citizen.phone == phone, Citizen.is_deleted == False)
            )
            if exclude_id:
                query = query.filter(Citizen.id != exclude_id)
            return query.first() is not None
        except Exception as e:
            logger.error(f"Error checking phone existence: {str(e)}")
            raise DatabaseError(f"Failed to check phone: {str(e)}")

    def aadhaar_exists(self, aadhaar: str, exclude_id: Optional[str] = None) -> bool:
        """Check if Aadhaar exists"""
        try:
            if not aadhaar:
                return False
            query = self.db.query(Citizen).filter(
                and_(Citizen.aadhaar_number == aadhaar, Citizen.is_deleted == False)
            )
            if exclude_id:
                query = query.filter(Citizen.id != exclude_id)
            return query.first() is not None
        except Exception as e:
            logger.error(f"Error checking Aadhaar existence: {str(e)}")
            raise DatabaseError(f"Failed to check Aadhaar: {str(e)}")

    def ration_card_exists(
        self, ration_card: str, exclude_id: Optional[str] = None
    ) -> bool:
        """Check if Ration Card exists"""
        try:
            if not ration_card:
                return False
            query = self.db.query(Citizen).filter(
                and_(
                    Citizen.smart_ration_card == ration_card,
                    Citizen.is_deleted == False,
                )
            )
            if exclude_id:
                query = query.filter(Citizen.id != exclude_id)
            return query.first() is not None
        except Exception as e:
            logger.error(f"Error checking Ration Card existence: {str(e)}")
            raise DatabaseError(f"Failed to check Ration Card: {str(e)}")

    def update(self, citizen_id: str, update_data: dict) -> Optional[Citizen]:
        """Update citizen"""
        try:
            citizen = self.get_by_id(citizen_id)
            if not citizen:
                raise NotFoundError("Citizen not found")

            for key, value in update_data.items():
                if value is not None and hasattr(citizen, key):
                    setattr(citizen, key, value)

            self.db.commit()
            self.db.refresh(citizen)
            logger.info(f"Citizen updated: {citizen_id}")
            return citizen
        except NotFoundError:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating citizen: {str(e)}")
            raise DatabaseError(f"Failed to update citizen: {str(e)}")

    def delete(self, citizen_id: str) -> bool:
        """Soft delete citizen"""
        try:
            citizen = self.get_by_id(citizen_id)
            if not citizen:
                raise NotFoundError("Citizen not found")

            citizen.is_deleted = True
            citizen.account_active = False
            self.db.commit()
            logger.info(f"Citizen deleted: {citizen_id}")
            return True
        except NotFoundError:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting citizen: {str(e)}")
            raise DatabaseError(f"Failed to delete citizen: {str(e)}")

    def list_all(self, skip: int = 0, limit: int = 100) -> List[Citizen]:
        """List all citizens"""
        try:
            return (
                self.db.query(Citizen)
                .filter(Citizen.is_deleted == False)
                .offset(skip)
                .limit(limit)
                .all()
            )
        except Exception as e:
            logger.error(f"Error listing citizens: {str(e)}")
            raise DatabaseError(f"Failed to list citizens: {str(e)}")

    def get_count(self) -> int:
        """Get total citizen count"""
        try:
            return self.db.query(Citizen).filter(Citizen.is_deleted == False).count()
        except Exception as e:
            logger.error(f"Error counting citizens: {str(e)}")
            raise DatabaseError(f"Failed to count citizens: {str(e)}")


class LoginAuditRepository:
    """Repository for Login Audit operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, audit_data: dict) -> LoginAudit:
        """Create login audit record"""
        try:
            audit = LoginAudit(**audit_data)
            self.db.add(audit)
            self.db.commit()
            self.db.refresh(audit)
            logger.info(f"Login audit created for citizen: {audit_data.get('citizen_id')}")
            return audit
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating login audit: {str(e)}")
            raise DatabaseError(f"Failed to create audit record: {str(e)}")

    def get_by_citizen(
        self, citizen_id: str, limit: int = 10
    ) -> List[LoginAudit]:
        """Get login audits for citizen"""
        try:
            return (
                self.db.query(LoginAudit)
                .filter(LoginAudit.citizen_id == citizen_id)
                .order_by(LoginAudit.created_at.desc())
                .limit(limit)
                .all()
            )
        except Exception as e:
            logger.error(f"Error fetching login audits: {str(e)}")
            raise DatabaseError(f"Failed to fetch audit records: {str(e)}")

    def get_recent_failed_attempts(
        self, citizen_id: str, minutes: int = 30
    ) -> List[LoginAudit]:
        """Get recent failed login attempts"""
        from datetime import datetime, timedelta

        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
            return (
                self.db.query(LoginAudit)
                .filter(
                    and_(
                        LoginAudit.citizen_id == citizen_id,
                        LoginAudit.success == False,
                        LoginAudit.created_at >= cutoff_time,
                    )
                )
                .all()
            )
        except Exception as e:
            logger.error(f"Error fetching failed login attempts: {str(e)}")
            raise DatabaseError(f"Failed to fetch audit records: {str(e)}")
