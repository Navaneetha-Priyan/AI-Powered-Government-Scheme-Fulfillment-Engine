"""Document upload, extraction, review, and profile-confirmation workflow.

The API layer deliberately does not know how documents are stored or parsed.  A
future OCR provider or vector/document service can therefore replace this class
without changing the citizen-profile or recommendation modules.
"""
import json
import re
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.citizen_document import (
    CitizenDocumentType,
    DocumentProcessStatus,
    ExtractedInformation,
    ProfileConflict,
    ProfileVerification,
    UploadedDocument,
    VerificationStatus,
)
from app.models.citizen_profile import LandRecord
from app.repositories.citizen_profile_repository import CitizenProfileRepository


class DocumentIntelligenceService:
    ALLOWED = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
    PRIORITY = {
        CitizenDocumentType.AADHAAR_CARD: 1,
        CitizenDocumentType.INCOME_CERTIFICATE: 2,
        CitizenDocumentType.COMMUNITY_CERTIFICATE: 2,
        CitizenDocumentType.DISABILITY_CERTIFICATE: 2,
        CitizenDocumentType.SMART_RATION_CARD: 3,
        CitizenDocumentType.LAND_DOCUMENT: 3,
        CitizenDocumentType.FARMER_DOCUMENT: 3,
        CitizenDocumentType.BANK_PASSBOOK: 4,
        CitizenDocumentType.EDUCATION_CERTIFICATE: 4,
    }
    PROFILE_FIELDS = {
        "annual_income", "income_category", "caste", "community", "sub_caste",
        "farmer_id", "is_farmer", "disability_type", "disability_percentage",
        "education_level", "education_institution",
    }

    def __init__(self, db: Session):
        self.db = db
        self.profiles = CitizenProfileRepository(db)

    def upload(self, citizen_id: str, file: UploadFile, document_type: CitizenDocumentType):
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in self.ALLOWED:
            raise ValueError("Only PDF, PNG, JPG, and JPEG documents are allowed")
        raw = file.file.read()
        if not raw or len(raw) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise ValueError("Invalid or oversized document")
        if self.db.query(UploadedDocument).filter_by(citizen_id=citizen_id, document_type=document_type).first():
            raise ValueError(f"{document_type.value} has already been uploaded")

        location = Path(settings.DOCUMENT_STORAGE_DIR) / citizen_id
        location.mkdir(parents=True, exist_ok=True)
        target = location / f"{uuid4()}{suffix}"
        target.write_bytes(raw)
        document = UploadedDocument(
            citizen_id=citizen_id, document_type=document_type,
            original_file_name=file.filename, file_path=str(target), file_size=len(raw),
            mime_type=self.ALLOWED[suffix],
        )
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def process(self, citizen_id: str, document_id: str):
        document = self._owned(citizen_id, document_id)
        document.upload_status = DocumentProcessStatus.PROCESSING
        self.db.commit()
        try:
            text = self._extract_text(Path(document.file_path))
            self.db.query(ExtractedInformation).filter_by(document_id=document.id).delete()
            fields = self._fields(text, document.document_type)
            self.db.add_all([
                ExtractedInformation(document_id=document.id, field_name=name, field_value=value, confidence_score=0.85)
                for name, value in fields.items()
            ])
            document.upload_status = DocumentProcessStatus.NEEDS_REVIEW if fields else DocumentProcessStatus.PROCESSED
            document.processing_error = None
            self.db.commit()
            return fields
        except Exception as exc:
            document.upload_status = DocumentProcessStatus.FAILED
            document.processing_error = str(exc)
            self.db.commit()
            raise

    def documents(self, citizen_id: str):
        return self.db.query(UploadedDocument).filter_by(citizen_id=citizen_id).order_by(UploadedDocument.created_at.desc()).all()

    def extracted(self, citizen_id: str, document_id: str):
        document = self._owned(citizen_id, document_id)
        return self.db.query(ExtractedInformation).filter_by(document_id=document.id).all()

    def process_all(self, citizen_id: str):
        results = []
        for document in self.documents(citizen_id):
            if document.upload_status in {DocumentProcessStatus.UPLOADED, DocumentProcessStatus.FAILED}:
                try:
                    results.append({"document_id": document.id, "status": "processed", "fields": self.process(citizen_id, document.id)})
                except Exception as exc:
                    results.append({"document_id": document.id, "status": "failed", "error": str(exc)})
        return results

    def preview(self, citizen_id: str):
        """Return the preferred value for each field and recreate unresolved conflicts."""
        self.db.query(ProfileConflict).filter_by(citizen_id=citizen_id, is_resolved=False).delete()
        selected, sources = {}, {}
        rows = self.db.query(ExtractedInformation, UploadedDocument).join(UploadedDocument).filter(
            UploadedDocument.citizen_id == citizen_id,
            UploadedDocument.upload_status.in_([DocumentProcessStatus.PROCESSED, DocumentProcessStatus.NEEDS_REVIEW]),
        ).all()
        for field, document in rows:
            name, value = field.field_name, field.field_value
            if name not in selected:
                selected[name], sources[name] = value, document
                continue
            if selected[name] == value:
                continue
            prior_document, prior_value = sources[name], selected[name]
            if self.PRIORITY.get(document.document_type, 99) < self.PRIORITY.get(prior_document.document_type, 99):
                primary_document, primary_value = document, value
                conflicting_document, conflicting_value = prior_document, prior_value
                selected[name], sources[name] = value, document
            else:
                primary_document, primary_value = prior_document, prior_value
                conflicting_document, conflicting_value = document, value
            self.db.add(ProfileConflict(
                citizen_id=citizen_id, field_name=name,
                primary_document_id=primary_document.id, primary_value=primary_value,
                conflicting_document_id=conflicting_document.id, conflicting_value=conflicting_value,
            ))
        self.db.commit()
        conflicts = self.db.query(ProfileConflict).filter_by(citizen_id=citizen_id, is_resolved=False).all()
        return selected, conflicts

    def generate_profile(self, citizen_id: str):
        """Persist only reviewed fields; this is called by final confirmation."""
        rows = self.db.query(ExtractedInformation).join(UploadedDocument).filter(
            UploadedDocument.citizen_id == citizen_id, ExtractedInformation.is_verified.is_(True)
        ).all()
        data = {row.field_name: row.field_value for row in rows}
        profile_data = {name: self._profile_value(name, value) for name, value in data.items() if name in self.PROFILE_FIELDS}
        profile = self.profiles.upsert(citizen_id, profile_data)
        self._upsert_land_record(citizen_id, data)
        return profile, data

    def verify(self, citizen_id: str, document_id: str, approved: dict):
        rows = self.extracted(citizen_id, document_id)
        for row in rows:
            if row.field_name in approved:
                row.field_value, row.is_verified = approved[row.field_name], True
        return self._save_verification(citizen_id, rows)

    def correct(self, citizen_id: str, field_name: str, value: str):
        fields = self.db.query(ExtractedInformation).join(UploadedDocument).filter(
            UploadedDocument.citizen_id == citizen_id, ExtractedInformation.field_name == field_name
        ).all()
        if not fields:
            raise ValueError("Extracted field not found")
        # A correction is a user-confirmed value, so apply it to every competing source.
        for field in fields:
            field.field_value, field.is_verified = value, True
        self.db.query(ProfileConflict).filter_by(citizen_id=citizen_id, field_name=field_name, is_resolved=False).update({"is_resolved": True})
        self.db.commit()
        return fields[0]

    def completeness(self, citizen_id: str):
        fields, _ = self.preview(citizen_id)
        groups = {
            "identity": {"full_name", "date_of_birth", "gender", "address", "pincode"},
            "financial": {"annual_income"}, "social": {"caste", "community"},
            "agriculture": {"survey_number", "land_area", "farmer_id"},
            "banking": {"bank_name", "ifsc", "masked_account_number"},
            "education": {"education_level", "education_institution"},
        }
        result = {group: round(100 * len(required & fields.keys()) / len(required)) for group, required in groups.items()}
        result["overall"] = round(sum(result.values()) / len(result))
        return result

    def confirm(self, citizen_id: str):
        fields, conflicts = self.preview(citizen_id)
        if conflicts:
            raise ValueError("Resolve all profile conflicts before confirmation")
        rows = self.db.query(ExtractedInformation).join(UploadedDocument).filter(UploadedDocument.citizen_id == citizen_id).all()
        for row in rows:
            row.is_verified = True
        self.db.flush()
        profile, _ = self.generate_profile(citizen_id)
        verification = self.db.query(ProfileVerification).filter_by(citizen_id=citizen_id).first() or ProfileVerification(citizen_id=citizen_id)
        verification.verified_fields, verification.pending_fields = json.dumps(sorted(fields)), "[]"
        verification.verification_status = VerificationStatus.VERIFIED
        for document in self.documents(citizen_id):
            if document.upload_status in {DocumentProcessStatus.PROCESSED, DocumentProcessStatus.NEEDS_REVIEW}:
                document.upload_status, document.verification_status = DocumentProcessStatus.VERIFIED, VerificationStatus.VERIFIED
        self.db.add(verification)
        self.db.commit()
        return profile

    def _owned(self, citizen_id: str, document_id: str):
        document = self.db.query(UploadedDocument).filter_by(id=document_id, citizen_id=citizen_id).first()
        if not document:
            raise ValueError("Document not found")
        return document

    def _save_verification(self, citizen_id: str, rows):
        verified = [row.field_name for row in rows if row.is_verified]
        pending = [row.field_name for row in rows if not row.is_verified]
        record = self.db.query(ProfileVerification).filter_by(citizen_id=citizen_id).first() or ProfileVerification(citizen_id=citizen_id)
        record.verified_fields, record.pending_fields = json.dumps(verified), json.dumps(pending)
        record.verification_status = VerificationStatus.VERIFIED if not pending else VerificationStatus.PENDING
        self.db.add(record)
        self.db.commit()
        return record

    def _upsert_land_record(self, citizen_id: str, data: dict):
        if not any(name in data for name in {"survey_number", "land_area", "ownership_type", "patta_number"}):
            return
        record = self.db.query(LandRecord).filter_by(citizen_id=citizen_id, survey_number=data.get("survey_number")).first()
        if record is None:
            record = LandRecord(citizen_id=citizen_id, survey_number=data.get("survey_number"))
            self.db.add(record)
        for name in ("survey_number", "ownership_type", "patta_number", "village", "taluk", "district", "state"):
            if data.get(name):
                setattr(record, name, data[name])
        if data.get("land_area"):
            record.land_area = float(data["land_area"])

    @staticmethod
    def _profile_value(name: str, value: str):
        if name == "annual_income":
            return float(value.replace(",", ""))
        if name == "disability_percentage":
            return int(value)
        if name in {"is_farmer", "is_disabled"}:
            return value.lower() == "true"
        return value

    def _extract_text(self, path: Path):
        if path.suffix.lower() == ".pdf":
            import fitz
            with fitz.open(path) as pdf:
                return "".join(page.get_text() for page in pdf)
        try:
            import pytesseract
            from PIL import Image
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
            return pytesseract.image_to_string(Image.open(path))
        except ImportError as exc:
            raise ValueError("Image OCR provider is not installed") from exc

    def _fields(self, text: str, kind: CitizenDocumentType):
        patterns = {
            "full_name": r"(?:name|holder name|student name)\s*[:\-]\s*([^\n]+)",
            "date_of_birth": r"(?:dob|date of birth)\s*[:\-]\s*([\d/\-]+)",
            "gender": r"(?:gender|sex)\s*[:\-]\s*(male|female|other)",
            "address": r"(?:address)\s*[:\-]\s*([^\n]+)", "pincode": r"(?:pincode|pin code)\s*[:\-]?\s*(\d{6})",
            "annual_income": r"(?:annual income|income)\s*[:\-]?\s*(?:₹|Rs\.?\s*)?([\d,]+)",
            "income_category": r"(?:income category)\s*[:\-]\s*([^\n]+)", "caste": r"(?:caste)\s*[:\-]\s*([^\n]+)",
            "community": r"(?:community)\s*[:\-]\s*([^\n]+)", "sub_caste": r"(?:sub[ -]?category|sub caste)\s*[:\-]\s*([^\n]+)",
            "survey_number": r"(?:survey\s*(?:no|number)?)\s*[:\-]\s*([^\n]+)", "land_area": r"(?:land area|area)\s*[:\-]\s*([\d.]+)",
            "ownership_type": r"(?:ownership)\s*[:\-]\s*([^\n]+)", "patta_number": r"(?:patta\s*(?:no|number)?)\s*[:\-]\s*([^\n]+)",
            "farmer_id": r"(?:farmer\s*id)\s*[:\-]\s*([^\n]+)", "disability_percentage": r"(?:disability)\s*[:\-]?\s*(\d{1,3})\s*%",
            "disability_type": r"(?:disability type)\s*[:\-]\s*([^\n]+)", "bank_name": r"(?:bank name|bank)\s*[:\-]\s*([^\n]+)",
            "ifsc": r"(?:ifsc)\s*[:\-]?\s*([A-Z]{4}0[A-Z0-9]{6})", "education_level": r"(?:qualification|degree)\s*[:\-]\s*([^\n]+)",
            "education_institution": r"(?:institution|college|school)\s*[:\-]\s*([^\n]+)",
        }
        output = {}
        for name, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                output[name] = match.group(1).strip().replace(",", "")
        account = re.search(r"(?:account(?: number| no)?)\s*[:\-]?\s*(\d{8,18})", text, re.IGNORECASE)
        if account:
            output["masked_account_number"] = f"{'*' * max(0, len(account.group(1)) - 4)}{account.group(1)[-4:]}"
        if kind == CitizenDocumentType.FARMER_DOCUMENT:
            output["is_farmer"] = "true"
        if kind == CitizenDocumentType.DISABILITY_CERTIFICATE:
            output["is_disabled"] = "true"
        return output
