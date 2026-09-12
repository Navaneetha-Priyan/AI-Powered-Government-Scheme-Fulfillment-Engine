"""Manual profile-to-eligibility integration runner.

This script is an investigation aid, not a permanent pytest suite. It exercises
the existing document upload/review/confirmation flow against realistic mock
DigiLocker document metadata, reloads the persisted citizen profile, and then
runs the existing structured eligibility/recommendation services.

Run from backend/:
    python scripts/test_profile_to_eligibility.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Import models so Base.metadata sees every table needed by the services.
from app.core.config import settings  # noqa: E402
from app.database.connection import Base  # noqa: E402
from app.models import citizen as _citizen_models  # noqa: F401,E402
from app.models import citizen_document as _citizen_document_models  # noqa: F401,E402
from app.models import citizen_profile as _profile_models  # noqa: F401,E402
from app.models import digilocker as _digilocker_models  # noqa: F401,E402
from app.models import government_scheme as _scheme_models  # noqa: F401,E402
from app.models import recommendation as _recommendation_models  # noqa: F401,E402
from app.models.citizen import Citizen, Gender  # noqa: E402
from app.models.citizen_document import CitizenDocumentType  # noqa: E402
from app.models.government_scheme import GovernmentScheme, SchemeStatus  # noqa: E402
from app.repositories.citizen_profile_repository import (  # noqa: E402
    CitizenProfileRepository,
    LandRecordRepository,
)
from app.services.document_intelligence_service import DocumentIntelligenceService  # noqa: E402
from app.services.eligibility_catalog_service import (  # noqa: E402
    get_catalogue_entry,
    load_eligibility_catalogue,
)
from app.services.eligibility_evaluator import EligibilityEvaluator  # noqa: E402
from app.services.recommendation_service import (  # noqa: E402
    CitizenContextService,
    RecommendationService,
)
from app.utils.mock_digilocker_data import get_mock_documents  # noqa: E402


SELECTED_SCHEME_IDS = (
    "pm-kusum",
    "smam",
    "pm-kisan",
    "pmfby",
    "pm-vishwakarma",
    "pm-svanidhi",
    "jjm",
)

RELEVANT_FIELDS = (
    "age",
    "occupation",
    "is_farmer",
    "land_ownership",
    "land_area",
    "annual_income",
    "income_tax_payer",
    "government_employee_status",
    "gender",
    "caste",
    "community",
    "marital_status",
    "family_member_count",
    "enterprise_type",
)

UPLOAD_TYPE_BY_MOCK_TYPE = {
    "aadhaar": CitizenDocumentType.AADHAAR_CARD,
    "smart_ration_card": CitizenDocumentType.SMART_RATION_CARD,
    "income_certificate": CitizenDocumentType.INCOME_CERTIFICATE,
    "community_certificate": CitizenDocumentType.COMMUNITY_CERTIFICATE,
    "land_record": CitizenDocumentType.LAND_DOCUMENT,
    "farmer_id": CitizenDocumentType.FARMER_DOCUMENT,
    "disability_certificate": CitizenDocumentType.DISABILITY_CERTIFICATE,
}

LABELS = {
    "full_name": "Name",
    "date_of_birth": "Date of Birth",
    "gender": "Gender",
    "address_line1": "Address",
    "village": "Village",
    "taluk": "Taluk",
    "district": "District",
    "state": "State",
    "pincode": "Pincode",
    "card_number": "Card Number",
    "holder_name": "Holder Name",
    "card_type": "Card Type",
    "family_size": "Family Size",
    "annual_income": "Annual Income",
    "income_category": "Income Category",
    "financial_year": "Financial Year",
    "caste": "Caste",
    "community": "Community",
    "sub_caste": "Sub Caste",
    "religion": "Religion",
    "issuing_authority": "Issuing Authority",
    "owner_name": "Owner Name",
    "survey_number": "Survey Number",
    "land_area": "Land Area",
    "land_type": "Land Type",
    "ownership_type": "Ownership Type",
    "patta_number": "Patta Number",
    "farmer_id": "Farmer ID",
    "is_farmer": "Is Farmer",
    "occupation": "Occupation",
    "is_disabled": "Disability Status",
    "disability_percentage": "Disability Percentage",
}


@dataclass
class FieldCheck:
    field: str
    extracted_value: Any
    persisted_value: Any
    source_document: str | None
    classification: str
    consistency: str


class SimpleUpload:
    def __init__(self, filename: str, content: bytes) -> None:
        self.filename = filename
        self.file = BytesIO(content)


def make_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def seed_citizen(db: Session) -> Citizen:
    citizen = Citizen(
        email="profile-eligibility@example.com",
        phone="9812345670",
        password_hash="manual-script-only",
        full_name="Selvam Murugan",
        gender=Gender.MALE,
        date_of_birth=datetime(1991, 1, 15),
        aadhaar_number="234123456789",
        smart_ration_card="TN1234567890",
        address_line1="12 South Street",
        village="Periyakulam",
        taluk="Villupuram",
        district="Villupuram",
        state="Tamil Nadu",
        pincode="605602",
    )
    db.add(citizen)
    db.commit()
    db.refresh(citizen)
    return citizen


def seed_schemes(db: Session) -> dict[str, GovernmentScheme]:
    schemes: dict[str, GovernmentScheme] = {}
    for entry in load_eligibility_catalogue():
        if entry.scheme_id not in SELECTED_SCHEME_IDS:
            continue
        scheme = GovernmentScheme(
            scheme_name=entry.scheme_name,
            description=entry.notes or f"Manual integration seed for {entry.scheme_name}.",
            category="agriculture" if entry.beneficiary_scope in {"FARMER", "MULTI_LEVEL"} else "welfare",
            department="Manual Integration Seed",
            government_level="central",
            state=None,
            benefits="See source catalogue.",
            eligibility_summary=entry.notes or "",
            required_documents=", ".join(entry.evidence_requirements),
            application_process="See official scheme document.",
            official_link=None,
            language="en",
            status=SchemeStatus.ACTIVE,
            is_deleted=False,
        )
        db.add(scheme)
        db.flush()
        schemes[entry.scheme_id] = scheme
    db.commit()
    return schemes


def mock_documents_for(citizen: Citizen) -> list[dict[str, Any]]:
    return get_mock_documents(
        citizen_id=citizen.id,
        digilocker_record_id="manual-digilocker-record",
        aadhaar=citizen.aadhaar_number,
        ration_card=citizen.smart_ration_card,
        full_name=citizen.full_name,
        gender=citizen.gender.value if citizen.gender else None,
        date_of_birth=citizen.date_of_birth.date().isoformat() if citizen.date_of_birth else None,
        address_line1=citizen.address_line1,
        village=citizen.village,
        taluk=citizen.taluk,
        district=citizen.district,
        state=citizen.state,
        pincode=citizen.pincode,
    )


def render_pdf_bytes(data: dict[str, Any]) -> bytes:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PyMuPDF/fitz is required for this manual PDF upload scenario.") from exc

    document = fitz.open()
    page = document.new_page(width=595, height=842)
    lines = ["Citizen Document", ""]
    for key, value in data.items():
        if value is None:
            continue
        label = LABELS.get(key, key.replace("_", " ").title())
        if key == "land_area":
            unit = data.get("unit")
            rendered = f"{value} {unit}" if unit else str(value)
        elif key == "date_of_birth":
            try:
                rendered = datetime.fromisoformat(str(value)).strftime("%d/%m/%Y")
            except ValueError:
                rendered = str(value)
        elif key == "annual_income":
            try:
                rendered = str(int(float(value)))
            except (TypeError, ValueError):
                rendered = str(value)
        elif isinstance(value, bool):
            rendered = "true" if value else "false"
        else:
            rendered = str(value)
        lines.append(f"{label}: {rendered}")
    page.insert_text((72, 72), "\n".join(lines), fontsize=11)
    payload = document.tobytes()
    document.close()
    return payload


def upload_process_confirm_documents(
    db: Session,
    citizen: Citizen,
    temp_dir: Path,
) -> tuple[dict[str, tuple[Any, str]], list[dict[str, Any]]]:
    service = DocumentIntelligenceService(db)
    extracted_by_field: dict[str, tuple[Any, str]] = {}
    processed_documents: list[dict[str, Any]] = []
    uploaded_types: set[CitizenDocumentType] = set()

    for source in mock_documents_for(citizen):
        mock_type = str(source["document_type"])
        upload_type = UPLOAD_TYPE_BY_MOCK_TYPE.get(mock_type)
        if upload_type is None:
            processed_documents.append(
                {
                    "document": source["document_name"],
                    "document_type": mock_type,
                    "status": "not_applicable",
                    "reason": "No matching CitizenDocumentType in upload/review flow.",
                }
            )
            continue
        if upload_type in uploaded_types:
            processed_documents.append(
                {
                    "document": source["document_name"],
                    "document_type": mock_type,
                    "status": "not_applicable",
                    "reason": (
                        "Upload/review flow allows one document per CitizenDocumentType; "
                        "the first document of this type was already processed."
                    ),
                }
            )
            continue
        uploaded_types.add(upload_type)

        metadata = json.loads(source["doc_metadata"])
        pdf_name = f"{mock_type}_{source['document_number']}.pdf".replace("/", "_")
        pdf_bytes = render_pdf_bytes(metadata["data"])
        temp_pdf = temp_dir / pdf_name
        temp_pdf.write_bytes(pdf_bytes)

        uploaded = service.upload(
            citizen.id,
            SimpleUpload(pdf_name, pdf_bytes),
            upload_type,
            replace=False,
        )
        fields = service.process(citizen.id, uploaded.id)
        processed_documents.append(
            {
                "document": source["document_name"],
                "document_type": mock_type,
                "uploaded_document_id": uploaded.id,
                "fields": fields,
                "status": "processed",
            }
        )
        for field, value in fields.items():
            extracted_by_field.setdefault(field, (value, source["document_name"]))

    preview_fields, conflicts = service.preview(citizen.id)
    if conflicts:
        raise RuntimeError(f"Profile preview has unresolved conflicts: {[c.field_name for c in conflicts]}")
    confirmed_profile = service.confirm(citizen.id)
    db.refresh(confirmed_profile)
    for field, value in preview_fields.items():
        extracted_by_field.setdefault(field, (value, "profile preview"))
    return extracted_by_field, processed_documents


def value_of(profile: Any, citizen: Citizen, land_records: list[Any], field: str) -> Any:
    if field == "age":
        if not citizen.date_of_birth:
            return None
        today = datetime.utcnow().date()
        born = citizen.date_of_birth.date()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    if field == "gender":
        return citizen.gender.value if getattr(citizen.gender, "value", None) else citizen.gender
    if field == "land_ownership":
        values = [record.ownership_type for record in land_records if record.ownership_type]
        return values or None
    if field == "land_area":
        values = [record.land_area for record in land_records if record.land_area is not None]
        return sum(values) if values else None
    if hasattr(profile, field):
        value = getattr(profile, field)
        return value.value if getattr(value, "value", None) else value
    if hasattr(citizen, field):
        value = getattr(citizen, field)
        return value.value if getattr(value, "value", None) else value
    return None


def source_value_for(field: str, extracted: dict[str, tuple[Any, str]]) -> tuple[Any, str | None, str]:
    aliases = {
        "age": ("age", "date_of_birth"),
        "occupation": ("occupation",),
        "is_farmer": ("is_farmer",),
        "land_ownership": ("ownership_type",),
        "land_area": ("land_area",),
        "annual_income": ("annual_income",),
        "gender": ("gender",),
        "caste": ("caste",),
        "community": ("community",),
        "family_member_count": ("family_size",),
    }
    for candidate in aliases.get(field, (field,)):
        if candidate in extracted:
            value, source = extracted[candidate]
            return value, source, "present"
    return None, None, "absent"


def classify_field(
    field: str,
    extracted: dict[str, tuple[Any, str]],
    persisted: Any,
    representable: bool,
) -> tuple[Any, str | None, str]:
    source_value, source_doc, source_state = source_value_for(field, extracted)
    if not representable:
        return source_value, source_doc, "not applicable"
    if source_state == "absent":
        return None, None, "missing from source document"
    if persisted in (None, "", [], ()):
        return source_value, source_doc, "incorrectly extracted"
    if not values_match(source_value, persisted):
        return source_value, source_doc, "incorrectly extracted"
    return source_value, source_doc, "correctly extracted"


def normalize_compare_value(value: Any) -> Any:
    if isinstance(value, list):
        return [normalize_compare_value(item) for item in value]
    if getattr(value, "value", None) is not None:
        value = value.value
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().lower()
    if text in {"true", "yes", "y", "1"}:
        return True
    if text in {"false", "no", "n", "0"}:
        return False
    try:
        return float(text)
    except ValueError:
        return text


def values_match(source_value: Any, persisted_value: Any) -> bool:
    source = normalize_compare_value(source_value)
    persisted = normalize_compare_value(persisted_value)
    if isinstance(persisted, list):
        return source in persisted
    if isinstance(source, list):
        return persisted in source
    return source == persisted


def build_field_checks(
    extracted: dict[str, tuple[Any, str]],
    profile: Any,
    citizen: Citizen,
    land_records: list[Any],
) -> list[FieldCheck]:
    checks: list[FieldCheck] = []
    for field in RELEVANT_FIELDS:
        persisted = value_of(profile, citizen, land_records, field)
        representable = persisted is not None or hasattr(profile, field) or hasattr(citizen, field) or field in {
            "age",
            "gender",
            "land_ownership",
            "land_area",
        }
        source_value, source_doc, classification = classify_field(
            field, extracted, persisted, representable
        )
        consistency = "PASS"
        if classification == "correctly extracted" and persisted in (None, "", [], ()):
            consistency = "FAIL"
        if classification == "incorrectly extracted":
            consistency = "FAIL"
        checks.append(
            FieldCheck(
                field=field,
                extracted_value=source_value,
                persisted_value=persisted,
                source_document=source_doc,
                classification=classification,
                consistency=consistency,
            )
        )
    return checks


def condition_lines(conditions: Iterable[Any]) -> list[str]:
    lines = []
    for condition in conditions:
        lines.append(
            "    - "
            f"{condition.result or ('PASS' if condition.passed else 'FAIL')} "
            f"{condition.rule_id or condition.condition}: "
            f"field={condition.field or condition.condition}, "
            f"operator={condition.operator}, "
            f"expected={condition.expected_value!r}, "
            f"actual={condition.actual_value!r}, "
            f"mandatory={condition.mandatory}"
        )
    return lines


def evaluate_scheme(
    db: Session,
    citizen_id: str,
    scheme_id: str,
    seeded_schemes: dict[str, GovernmentScheme],
) -> Any:
    entry = get_catalogue_entry(scheme_id)
    if entry is None:
        raise RuntimeError(f"Catalogue entry not found: {scheme_id}")
    context = CitizenContextService(db).build(citizen_id)
    rich_result = EligibilityEvaluator().evaluate_catalogue_entry(entry, context)

    recommendation = RecommendationService(db).eligibility_check(
        citizen_id,
        scheme_id=seeded_schemes[scheme_id].id,
    )
    if recommendation.eligibility_status != rich_result.status:
        raise AssertionError(
            f"Recommendation status mismatch for {scheme_id}: "
            f"{recommendation.eligibility_status} != {rich_result.status}"
        )
    return rich_result


def print_documents(processed_documents: list[dict[str, Any]]) -> None:
    print("\nDOCUMENT PROCESSING")
    for item in processed_documents:
        print(f"- {item['document']} ({item['document_type']}): {item['status']}")
        if item.get("reason"):
            print(f"  reason: {item['reason']}")
        for field, value in sorted((item.get("fields") or {}).items()):
            print(f"  {field}: {value!r}")


def print_profile_checks(citizen: Citizen, checks: list[FieldCheck]) -> None:
    print("\nCITIZEN")
    print(f"- citizen id: {citizen.id}")

    print("\nEXTRACTED PROFILE / PERSISTED PROFILE / PROFILE CONSISTENCY")
    for check in checks:
        print(
            f"- {check.field}: extracted={check.extracted_value!r}"
            f" source={check.source_document or '-'}"
            f" persisted={check.persisted_value!r}"
            f" classification={check.classification}"
            f" consistency={check.consistency}"
        )


def print_eligibility_result(scheme_id: str, result: Any) -> None:
    entry = get_catalogue_entry(scheme_id)
    print("\nELIGIBILITY")
    print(f"- scheme: {result.scheme_name} ({scheme_id})")
    print(f"- beneficiary scope: {entry.beneficiary_scope if entry else '-'}")
    print(f"- final eligibility status: {result.status}")
    print(f"- evaluation_status: {result.evaluation_status}")
    print("- passed rules:")
    print("\n".join(condition_lines(result.matched_conditions)) or "    - none")
    print("- failed rules:")
    print("\n".join(condition_lines(result.failed_conditions)) or "    - none")
    print("- unknown rules:")
    print("\n".join(condition_lines(result.missing_information)) or "    - none")
    print(f"- missing profile information: {[c.field for c in result.missing_information]}")
    print(f"- missing evidence: {result.missing_evidence}")
    manual_reason = next(
        (c.notes for c in result.missing_information if c.operator == "manual_review"),
        None,
    )
    if manual_reason:
        print(f"- manual-review reason: {manual_reason}")


def run_mutation_tests(
    db: Session,
    citizen: Citizen,
    seeded_schemes: dict[str, GovernmentScheme],
) -> None:
    profile_repo = CitizenProfileRepository(db)
    profile = profile_repo.get_by_citizen_id(citizen.id)
    if profile is None:
        raise RuntimeError("Cannot run mutations without a persisted profile.")

    print("\nMUTATION TEST 1")
    baseline = evaluate_scheme(db, citizen.id, "smam", seeded_schemes)
    original_is_farmer = profile.is_farmer
    original_occupation = profile.occupation
    profile.is_farmer = False
    profile.occupation = "Shopkeeper"
    db.commit()
    mutated = evaluate_scheme(db, citizen.id, "smam", seeded_schemes)
    print(f"- changed profile.is_farmer {original_is_farmer!r} -> False")
    print(f"- baseline SMAM status: {baseline.status}")
    print(f"- mutated SMAM status: {mutated.status}")
    if mutated.status != "not_eligible":
        raise AssertionError("SMAM should become not_eligible after farmer status is set false.")

    profile.is_farmer = original_is_farmer
    profile.occupation = original_occupation
    db.commit()

    print("\nMUTATION TEST 2")
    profile.is_farmer = None
    db.commit()
    unknown = evaluate_scheme(db, citizen.id, "smam", seeded_schemes)
    print("- changed profile.is_farmer -> None")
    print(f"- missing-field SMAM status: {unknown.status}")
    if unknown.status != "insufficient_information":
        raise AssertionError(
            "SMAM should become insufficient_information when required farmer status is unknown."
        )
    profile.is_farmer = original_is_farmer
    profile.occupation = original_occupation
    db.commit()


def report_missing_profile_fields() -> None:
    print("\nMISSING PROFILE FIELDS LIMITING EVALUATION")
    for scheme_id in SELECTED_SCHEME_IDS:
        entry = get_catalogue_entry(scheme_id)
        if entry and entry.missing_profile_fields:
            print(f"- {scheme_id}: {', '.join(entry.missing_profile_fields)}")


def main() -> int:
    db = make_session()
    with tempfile.TemporaryDirectory(prefix="profile-eligibility-") as raw_temp_dir:
        temp_dir = Path(raw_temp_dir)
        settings.DOCUMENT_STORAGE_DIR = str(temp_dir / "uploaded")

        citizen = seed_citizen(db)
        seeded_schemes = seed_schemes(db)

        extracted, processed_documents = upload_process_confirm_documents(
            db,
            citizen,
            temp_dir,
        )
        db.expire_all()
        persisted_citizen = db.query(Citizen).filter_by(id=citizen.id).first()
        profile = CitizenProfileRepository(db).get_by_citizen_id(citizen.id)
        land_records = LandRecordRepository(db).get_by_citizen_id(citizen.id)
        if persisted_citizen is None or profile is None:
            raise RuntimeError("Profile confirmation did not persist a citizen profile.")

        print_documents(processed_documents)
        print_profile_checks(
            persisted_citizen,
            build_field_checks(extracted, profile, persisted_citizen, land_records),
        )

        for scheme_id in SELECTED_SCHEME_IDS:
            result = evaluate_scheme(db, citizen.id, scheme_id, seeded_schemes)
            print_eligibility_result(scheme_id, result)

        run_mutation_tests(db, persisted_citizen, seeded_schemes)
        report_missing_profile_fields()

    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
