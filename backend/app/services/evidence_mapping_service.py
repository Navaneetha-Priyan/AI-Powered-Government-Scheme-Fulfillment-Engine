"""Central evidence-requirement mapping for scheme eligibility.

The eligibility engine reports evidence/profile requirements as raw keys
(``identity_proof``, ``land_record``, ``income_tax_payer``).  The upload
flow only supports the nine ``CitizenDocumentType`` slots.  This module is
the single explicit mapping between them so the UI can route each
requirement to an upload option, a profile question, or manual evidence.
It never hides requirements and never marks one satisfied by similarity:
satisfaction needs an actual accepted upload in ``document_types``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

DOC_AADHAAR = "aadhaar_card"
DOC_RATION = "smart_ration_card"
DOC_INCOME = "income_certificate"
DOC_COMMUNITY = "community_certificate"
DOC_LAND = "land_document"
DOC_FARMER = "farmer_document"
DOC_DISABILITY = "disability_certificate"
DOC_BANK = "bank_passbook"
DOC_EDUCATION = "education_certificate"

SUPPORTED_DOCUMENT_TYPES: frozenset[str] = frozenset(
    {
        DOC_AADHAAR,
        DOC_RATION,
        DOC_INCOME,
        DOC_COMMUNITY,
        DOC_LAND,
        DOC_FARMER,
        DOC_DISABILITY,
        DOC_BANK,
        DOC_EDUCATION,
    }
)


@dataclass(frozen=True)
class EvidenceMapping:
    requirement: str
    label: str
    kind: str
    document_types: tuple[str, ...] = ()
    profile_field: str | None = None
    profile_prompt: str | None = None
    note: str | None = None


_DOCUMENT_MAPPINGS: dict[str, EvidenceMapping] = {}


def _doc(
    requirement: str,
    label: str,
    *document_types: str,
    note: str | None = None,
) -> EvidenceMapping:
    mapping = EvidenceMapping(
        requirement=requirement,
        label=label,
        kind="document",
        document_types=tuple(document_types),
        note=note,
    )
    _DOCUMENT_MAPPINGS[requirement] = mapping
    return mapping


_doc("aadhaar", "Aadhaar", DOC_AADHAAR)
_doc("identity_proof", "Identity proof", DOC_AADHAAR)
_doc("address_proof", "Residence proof", DOC_AADHAAR, DOC_RATION)
_doc("bank_account", "Bank account proof", DOC_BANK)
_doc("bank_passbook", "Bank account proof", DOC_BANK)
_doc("land_record", "Land record", DOC_LAND,
     note="Land record / patta proves ownership.")
_doc("land_ownership_proof", "Land ownership proof", DOC_LAND,
     note="Land record / patta proves ownership.")
_doc("farmer_id", "Farmer ID", DOC_FARMER)
_doc("farmer_registration", "Farmer ID", DOC_FARMER)
_doc("community_certificate", "Community certificate", DOC_COMMUNITY)
_doc("caste_certificate", "Community certificate", DOC_COMMUNITY)
_doc("income_proof", "Income proof", DOC_INCOME)
_doc("income_certificate", "Income proof", DOC_INCOME)
_doc("disability_certificate", "Disability certificate", DOC_DISABILITY)
_doc("ration_card", "Ration card", DOC_RATION)
_doc("education_certificate", "Education certificate", DOC_EDUCATION)

_PROFILE_MAPPINGS: dict[str, EvidenceMapping] = {}


def _profile(
    requirement: str,
    label: str,
    profile_field: str,
    prompt: str,
) -> EvidenceMapping:
    mapping = EvidenceMapping(
        requirement=requirement,
        label=label,
        kind="profile_info",
        profile_field=profile_field,
        profile_prompt=prompt,
    )
    _PROFILE_MAPPINGS[requirement] = mapping
    return mapping


_profile("income_tax_payer", "Income-tax payer status",
         "income_tax_payer", "Are you an income-tax payer?")
_profile("government_employee_status", "Government employment status",
         "government_employee_status", "Are you a government employee?")
_profile("professional_category", "Professional category",
         "professional_category", "What is your professional category?")
_profile("pension_amount", "Pension amount",
         "pension_amount", "What pension amount do you receive?")
_profile("street_vendor_proof", "Street vendor record",
         "street_vendor_status", "Are you registered as a street vendor?")
_profile("pregnancy_status", "Pregnancy status",
         "pregnancy_status", "Are you currently pregnant?")
_profile("child_age", "Child age",
         "child_age", "What is the child's age?")
_profile("annual_income", "Annual income",
         "annual_income", "What is your annual income?")


def get_mapping(requirement: str) -> EvidenceMapping | None:
    key = (requirement or "").strip().lower()
    if not key:
        return None
    if key in _DOCUMENT_MAPPINGS:
        return _DOCUMENT_MAPPINGS[key]
    return _PROFILE_MAPPINGS.get(key)


def humanize_requirement(requirement: str) -> str:
    mapping = get_mapping(requirement)
    if mapping is not None:
        return mapping.label
    text = (requirement or "").replace("_", " ").strip()
    return text.title() or "Requirement"


@dataclass
class EvidenceChecklistItem:
    requirement: str
    label: str
    kind: str
    status: str
    document_types: list[str] = field(default_factory=list)
    matched_document_type: str | None = None
    profile_field: str | None = None
    profile_prompt: str | None = None
    note: str | None = None

    def to_dict(self) -> dict:
        return {
            "requirement": self.requirement,
            "label": self.label,
            "kind": self.kind,
            "status": self.status,
            "document_types": list(self.document_types),
            "matched_document_type": self.matched_document_type,
            "profile_field": self.profile_field,
            "profile_prompt": self.profile_prompt,
            "note": self.note,
        }


def resolve_evidence_checklist(
    requirements: Sequence[str] | None,
    uploaded_document_types: Iterable[str] | Mapping[str, object] | None,
    *,
    missing_only: Sequence[str] | None = None,
) -> list[EvidenceChecklistItem]:
    raw: list[str] = []
    for item in requirements or []:
        key = str(item or "").strip().lower()
        if key and key not in raw:
            raw.append(key)

    if isinstance(uploaded_document_types, Mapping):
        uploaded = {str(k).strip().lower() for k in uploaded_document_types}
    else:
        uploaded = {
            str(t or "").strip().lower() for t in uploaded_document_types or []
        }

    missing: set[str] | None = None
    if missing_only is not None:
        missing = {str(m or "").strip().lower() for m in missing_only}

    items: list[EvidenceChecklistItem] = []
    for key in raw:
        mapping = get_mapping(key)
        if mapping is None:
            items.append(EvidenceChecklistItem(
                requirement=key,
                label=humanize_requirement(key),
                kind="manual",
                status="manual",
                note="Additional scheme-specific evidence may be required.",
            ))
            continue
        if mapping.kind == "profile_info":
            is_missing = True if missing is None else key in missing
            items.append(EvidenceChecklistItem(
                requirement=key,
                label=mapping.label,
                kind="profile_info",
                status="needed" if is_missing else "available",
                profile_field=mapping.profile_field,
                profile_prompt=mapping.profile_prompt,
            ))
            continue
        matched = next(
            (doc for doc in mapping.document_types if doc in uploaded),
            None,
        )
        if missing is not None and key not in missing:
            status = "available" if matched else "manual"
        else:
            status = "available" if matched else "needed"
        items.append(EvidenceChecklistItem(
            requirement=key,
            label=mapping.label,
            kind="document",
            status=status,
            document_types=list(mapping.document_types),
            matched_document_type=matched,
            note=mapping.note,
        ))
    return items


def supported_mappings() -> list[EvidenceMapping]:
    return sorted(
        _DOCUMENT_MAPPINGS.values(), key=lambda item: item.requirement
    )


def manual_requirements_in_catalogue(catalogue_entries) -> list[str]:
    keys: set[str] = set()
    for entry in catalogue_entries or []:
        for raw in getattr(entry, "evidence_requirements", None) or []:
            key = str(raw or "").strip().lower()
            if not key:
                continue
            mapping = get_mapping(key)
            if mapping is None or mapping.kind != "document":
                keys.add(key)
    return sorted(keys)
