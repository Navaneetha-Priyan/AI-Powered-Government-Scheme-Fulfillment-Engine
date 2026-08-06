"""Repository layer for Module 3 knowledge-base records."""
from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.exceptions.exceptions import DatabaseError
from app.models.government_scheme import GovernmentScheme, SchemeDocument, SchemeChunk

logger = get_logger(__name__)


class GovernmentSchemeRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> GovernmentScheme:
        try:
            item = GovernmentScheme(**data)
            self.db.add(item)
            self.db.commit()
            self.db.refresh(item)
            return item
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError(f"Failed to create scheme: {exc}") from exc

    def get(self, scheme_id: str, include_deleted: bool = False) -> Optional[GovernmentScheme]:
        query = self.db.query(GovernmentScheme).filter(GovernmentScheme.id == scheme_id)
        if not include_deleted:
            query = query.filter(GovernmentScheme.is_deleted == False)  # noqa: E712
        return query.first()

    def get_by_name(self, scheme_name: str, exclude_id: str | None = None) -> Optional[GovernmentScheme]:
        query = self.db.query(GovernmentScheme).filter(func.lower(GovernmentScheme.scheme_name) == scheme_name.lower())
        if exclude_id:
            query = query.filter(GovernmentScheme.id != exclude_id)
        return query.first()

    def list(
        self,
        skip: int = 0,
        limit: int = 20,
        category: str | None = None,
        status: str | None = None,
        query: str | None = None,
    ) -> list[GovernmentScheme]:
        q = self.db.query(GovernmentScheme).filter(GovernmentScheme.is_deleted == False)  # noqa: E712
        if category:
            q = q.filter(func.lower(GovernmentScheme.category) == category.lower())
        if status:
            q = q.filter(func.lower(GovernmentScheme.status) == status.lower())
        if query:
            like = f"%{query.strip()}%"
            q = q.filter(
                or_(
                    GovernmentScheme.scheme_name.ilike(like),
                    GovernmentScheme.description.ilike(like),
                    GovernmentScheme.category.ilike(like),
                    GovernmentScheme.department.ilike(like),
                    GovernmentScheme.benefits.ilike(like),
                    GovernmentScheme.eligibility_summary.ilike(like),
                )
            )
        return q.order_by(GovernmentScheme.created_at.desc()).offset(skip).limit(limit).all()

    def count(self, category: str | None = None, status: str | None = None, query: str | None = None) -> int:
        q = self.db.query(func.count(GovernmentScheme.id)).filter(GovernmentScheme.is_deleted == False)  # noqa: E712
        if category:
            q = q.filter(func.lower(GovernmentScheme.category) == category.lower())
        if status:
            q = q.filter(func.lower(GovernmentScheme.status) == status.lower())
        if query:
            like = f"%{query.strip()}%"
            q = q.filter(
                or_(
                    GovernmentScheme.scheme_name.ilike(like),
                    GovernmentScheme.description.ilike(like),
                    GovernmentScheme.category.ilike(like),
                    GovernmentScheme.department.ilike(like),
                    GovernmentScheme.benefits.ilike(like),
                    GovernmentScheme.eligibility_summary.ilike(like),
                )
            )
        return int(q.scalar() or 0)

    def update(self, item: GovernmentScheme, data: dict) -> GovernmentScheme:
        try:
            for key, value in data.items():
                setattr(item, key, value)
            self.db.commit()
            self.db.refresh(item)
            return item
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError(f"Failed to update scheme: {exc}") from exc

    def delete(self, item: GovernmentScheme) -> None:
        try:
            item.is_deleted = True
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError(f"Failed to delete scheme: {exc}") from exc


class SchemeDocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> SchemeDocument:
        try:
            item = SchemeDocument(**data)
            self.db.add(item)
            self.db.commit()
            self.db.refresh(item)
            return item
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError(f"Failed to create scheme document: {exc}") from exc

    def get(self, document_id: str) -> Optional[SchemeDocument]:
        return self.db.query(SchemeDocument).filter(SchemeDocument.id == document_id).first()

    def list_by_scheme(self, scheme_id: str) -> list[SchemeDocument]:
        return (
            self.db.query(SchemeDocument)
            .filter(SchemeDocument.scheme_id == scheme_id)
            .order_by(SchemeDocument.version.desc(), SchemeDocument.created_at.desc())
            .all()
        )

    def get_latest_version(self, scheme_id: str) -> int:
        latest = self.db.query(func.max(SchemeDocument.version)).filter(SchemeDocument.scheme_id == scheme_id).scalar()
        return int(latest or 0)

    def get_chunks(self, document_id: str) -> list[SchemeChunk]:
        return self.db.query(SchemeChunk).filter(SchemeChunk.document_id == document_id).order_by(SchemeChunk.created_at.asc()).all()

    def get_chunks_by_scheme(self, scheme_id: str) -> list[SchemeChunk]:
        return self.db.query(SchemeChunk).filter(SchemeChunk.scheme_id == scheme_id).order_by(SchemeChunk.created_at.asc()).all()

    def clear_chunks(self, document_id: str) -> list[SchemeChunk]:
        chunks = self.get_chunks(document_id)
        if chunks:
            self.db.query(SchemeChunk).filter(SchemeChunk.document_id == document_id).delete(synchronize_session=False)
            self.db.commit()
        return chunks

    def add_chunks(self, chunks: Iterable[dict]) -> list[SchemeChunk]:
        try:
            items = [SchemeChunk(**chunk) for chunk in chunks]
            self.db.add_all(items)
            self.db.commit()
            for item in items:
                self.db.refresh(item)
            return items
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError(f"Failed to create scheme chunks: {exc}") from exc

    def set_processing_status(self, document: SchemeDocument, status, error: str | None = None) -> SchemeDocument:
        try:
            document.processing_status = status
            document.processing_error = error
            self.db.commit()
            self.db.refresh(document)
            return document
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError(f"Failed to update processing status: {exc}") from exc

    def delete_by_scheme(self, scheme_id: str) -> int:
        try:
            chunks_deleted = self.db.query(SchemeChunk).filter(SchemeChunk.scheme_id == scheme_id).delete(synchronize_session=False)
            documents_deleted = self.db.query(SchemeDocument).filter(SchemeDocument.scheme_id == scheme_id).delete(synchronize_session=False)
            self.db.commit()
            return int(chunks_deleted or 0) + int(documents_deleted or 0)
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError(f"Failed to delete scheme documents: {exc}") from exc
