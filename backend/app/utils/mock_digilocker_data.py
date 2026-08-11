"""Mock DigiLocker Seed Data — Simulates government digital repository records.

Each citizen's Aadhaar or Ration Card maps to a realistic mock profile
and a set of linked government documents. This is the single source of
truth for the DigiLocker sync operation.
"""
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional


# ─── Mock Profile Templates ────────────────────────────────────────────────────
# Keyed by aadhaar_number or smart_ration_card for lookup.
# In a real DigiLocker, this would be a secure government API call.

MOCK_PROFILES: Dict[str, Dict[str, Any]] = {
    # Profile 1 — BPL Farmer, Tamil Nadu
    "234123456789": {
        "father_name": "Murugan Selvam",
        "mother_name": "Kamala Murugan",
        "occupation": "Farmer",
        "marital_status": "married",
        "blood_group": "O+",
        "nationality": "Indian",
        "annual_income": 72000.0,
        "income_category": "bpl",
        "caste": "Vanniyar",
        "community": "MBC",
        "sub_caste": "Padayachi",
        "religion": "Hindu",
        "is_disabled": False,
        "disability_type": None,
        "disability_percentage": None,
        "is_farmer": True,
        "farmer_id": "TN-FARMER-001234",
        "education_level": "10th Standard",
        "education_institution": "Government High School, Villupuram",
        "family_member_count": 5,
        "family_details": '[{"name":"Kamala Murugan","relation":"Mother","age":55},{"name":"Priya Selvam","relation":"Wife","age":32},{"name":"Arjun Selvam","relation":"Son","age":10},{"name":"Kavya Selvam","relation":"Daughter","age":7}]',
    },
    # Profile 2 — EWS Urban, Tamil Nadu
    "499999999999": {
        "father_name": "Krishnamurthy Rajan",
        "mother_name": "Saraswathi Krishnamurthy",
        "occupation": "Daily Wage Laborer",
        "marital_status": "married",
        "blood_group": "A+",
        "nationality": "Indian",
        "annual_income": 120000.0,
        "income_category": "ews",
        "caste": "Nadar",
        "community": "BC",
        "sub_caste": None,
        "religion": "Hindu",
        "is_disabled": False,
        "disability_type": None,
        "disability_percentage": None,
        "is_farmer": False,
        "farmer_id": None,
        "education_level": "8th Standard",
        "education_institution": "Government Middle School, Chennai",
        "family_member_count": 4,
        "family_details": '[{"name":"Saraswathi Krishnamurthy","relation":"Mother","age":50},{"name":"Meena Rajan","relation":"Wife","age":30},{"name":"Karthik Rajan","relation":"Son","age":8}]',
    },
    # Profile 3 — Disabled citizen, APL
    "612345678907": {
        "father_name": "Suresh Babu",
        "mother_name": "Radha Suresh",
        "occupation": "Artisan",
        "marital_status": "single",
        "blood_group": "B+",
        "nationality": "Indian",
        "annual_income": 180000.0,
        "income_category": "apl",
        "caste": "Chettiar",
        "community": "OC",
        "sub_caste": None,
        "religion": "Hindu",
        "is_disabled": True,
        "disability_type": "Locomotor Disability",
        "disability_percentage": 45,
        "is_farmer": False,
        "farmer_id": None,
        "education_level": "12th Standard",
        "education_institution": "Government Higher Secondary School, Coimbatore",
        "family_member_count": 3,
        "family_details": '[{"name":"Suresh Babu","relation":"Father","age":60},{"name":"Radha Suresh","relation":"Mother","age":55}]',
    },
}

# Ration card → Aadhaar mapping for lookup
RATION_CARD_TO_AADHAAR: Dict[str, str] = {
    "TN1234567890": "234123456789",
    "TN0987654321": "499999999999",
    "TN1111222233": "612345678907",
}


def get_mock_profile(aadhaar: Optional[str], ration_card: Optional[str]) -> Optional[Dict[str, Any]]:
    """Resolve mock profile from Aadhaar or Ration Card"""
    if aadhaar and aadhaar in MOCK_PROFILES:
        return MOCK_PROFILES[aadhaar]
    if ration_card:
        aadhaar_from_card = RATION_CARD_TO_AADHAAR.get(ration_card.upper())
        if aadhaar_from_card:
            return MOCK_PROFILES.get(aadhaar_from_card)
    # Return a generic profile for any citizen without a specific mock record
    return _build_generic_profile()


def _build_generic_profile() -> Dict[str, Any]:
    """Build a generic profile for citizens without specific mock data"""
    return {
        "father_name": None,
        "mother_name": None,
        "occupation": "Not Specified",
        "marital_status": "single",
        "blood_group": None,
        "nationality": "Indian",
        "annual_income": None,
        "income_category": None,
        "caste": None,
        "community": None,
        "sub_caste": None,
        "religion": None,
        "is_disabled": False,
        "disability_type": None,
        "disability_percentage": None,
        "is_farmer": False,
        "farmer_id": None,
        "education_level": None,
        "education_institution": None,
        "family_member_count": None,
        "family_details": None,
    }


# ─── Mock Land Records ─────────────────────────────────────────────────────────

MOCK_LAND_RECORDS: Dict[str, list] = {
    "234123456789": [
        {
            "survey_number": "123/2A",
            "land_area": 2.5,
            "land_area_unit": "acres",
            "land_type": "agricultural",
            "village": "Periyakulam",
            "taluk": "Villupuram",
            "district": "Villupuram",
            "state": "Tamil Nadu",
            "ownership_type": "owned",
            "patta_number": "TN-VPM-2023-001",
        },
        {
            "survey_number": "456/1B",
            "land_area": 1.0,
            "land_area_unit": "acres",
            "land_type": "agricultural",
            "village": "Periyakulam",
            "taluk": "Villupuram",
            "district": "Villupuram",
            "state": "Tamil Nadu",
            "ownership_type": "inherited",
            "patta_number": "TN-VPM-2023-002",
        },
    ],
    "499999999999": [],
    "612345678907": [
        {
            "survey_number": "789/3C",
            "land_area": 0.25,
            "land_area_unit": "acres",
            "land_type": "residential",
            "village": "Gandhipuram",
            "taluk": "Coimbatore North",
            "district": "Coimbatore",
            "state": "Tamil Nadu",
            "ownership_type": "owned",
            "patta_number": "TN-CBE-2022-045",
        }
    ],
}


def get_mock_land_records(aadhaar: Optional[str], ration_card: Optional[str]) -> list:
    """Resolve mock land records from Aadhaar or Ration Card"""
    if aadhaar and aadhaar in MOCK_LAND_RECORDS:
        return MOCK_LAND_RECORDS[aadhaar]
    if ration_card:
        aadhaar_from_card = RATION_CARD_TO_AADHAAR.get(ration_card.upper())
        if aadhaar_from_card:
            return MOCK_LAND_RECORDS.get(aadhaar_from_card, [])
    return []


# ─── Mock Government Documents ─────────────────────────────────────────────────

_NOW = datetime.utcnow()
_BASE_URL = "https://mock-digilocker.gov.in/documents"


def get_mock_documents(
    citizen_id: str,
    digilocker_record_id: str,
    aadhaar: Optional[str],
    ration_card: Optional[str],
    full_name: str,
    gender: Optional[str] = None,
    date_of_birth: Optional[str] = None,
    address_line1: Optional[str] = None,
    village: Optional[str] = None,
    taluk: Optional[str] = None,
    district: Optional[str] = None,
    state: Optional[str] = None,
    pincode: Optional[str] = None,
) -> list:
    """
    Build mock government documents for a citizen.
    Every citizen gets a base set; specific Aadhaar numbers get additional docs.

    Each document's ``doc_metadata`` (a JSON string) contains realistic,
    structured fields matching what would actually be present on that document.
    This structured data is the foundation for the document → citizen-profile
    enrichment pipeline (Steps 2–4). Metadata is the document-level source of
    truth for profile enrichment; it is never read directly by the API layer.
    """
    docs = []

    # ── Resolve profile + land records for consistent structured metadata ──
    resolved_aadhaar = aadhaar
    if not resolved_aadhaar and ration_card:
        resolved_aadhaar = RATION_CARD_TO_AADHAAR.get(ration_card.upper())
    profile = get_mock_profile(resolved_aadhaar, ration_card) or _build_generic_profile()
    mock_land = get_mock_land_records(resolved_aadhaar, ration_card)
    first_land = mock_land[0] if mock_land else {}

    # Document-type labels kept in lowercase to match DocumentType enum values.
    metadata = lambda doc_type, data: json.dumps(
        {"document_type": doc_type, "data": data}
    )

    # Aadhaar card — always present if aadhaar is registered
    if aadhaar:
        docs.append({
            "citizen_id": citizen_id,
            "digilocker_record_id": digilocker_record_id,
            "document_type": "aadhaar",
            "document_number": aadhaar,
            "document_name": "Aadhaar Card",
            "issue_date": _NOW - timedelta(days=365 * 5),
            "expiry_date": None,
            "verification_status": "verified",
            "verified_by": "UIDAI",
            "verified_at": _NOW - timedelta(days=365 * 5),
            "download_url": f"{_BASE_URL}/aadhaar/{aadhaar}.pdf",
            "doc_metadata": metadata("aadhaar", {
                "full_name": full_name,
                "date_of_birth": date_of_birth,
                "gender": gender,
                "address_line1": address_line1,
                "village": village or first_land.get("village"),
                "taluk": taluk or first_land.get("taluk"),
                "district": district or first_land.get("district"),
                "state": state or first_land.get("state"),
                "pincode": pincode,
            }),
            "is_active": True,
        })

    # Smart Ration Card — always present if registered
    if ration_card:
        docs.append({
            "citizen_id": citizen_id,
            "digilocker_record_id": digilocker_record_id,
            "document_type": "smart_ration_card",
            "document_number": ration_card,
            "document_name": "Smart Ration Card",
            "issue_date": _NOW - timedelta(days=365 * 3),
            "expiry_date": _NOW + timedelta(days=365 * 2),
            "verification_status": "verified",
            "verified_by": "Tamil Nadu Civil Supplies Corporation",
            "verified_at": _NOW - timedelta(days=365 * 3),
            "download_url": f"{_BASE_URL}/ration-card/{ration_card}.pdf",
            "doc_metadata": metadata("ration_card", {
                "card_number": ration_card,
                "holder_name": full_name,
                "card_type": (profile.get("income_category") or "PHH").upper(),
                "family_size": profile.get("family_member_count"),
                "district": district or first_land.get("district"),
            }),
            "is_active": True,
        })

    # Income Certificate
    docs.append({
        "citizen_id": citizen_id,
        "digilocker_record_id": digilocker_record_id,
        "document_type": "income_certificate",
        "document_number": f"INC-{citizen_id[:8].upper()}",
        "document_name": "Income Certificate",
        "issue_date": _NOW - timedelta(days=180),
        "expiry_date": _NOW + timedelta(days=180),
        "verification_status": "verified",
        "verified_by": "Tahsildar Office",
        "verified_at": _NOW - timedelta(days=180),
        "download_url": f"{_BASE_URL}/income/{citizen_id}.pdf",
        "doc_metadata": metadata("income_certificate", {
            "holder_name": full_name,
            "annual_income": profile.get("annual_income"),
            "income_category": profile.get("income_category"),
            "financial_year": "2025-2026",
        }),
        "is_active": True,
    })

    # Community Certificate
    docs.append({
        "citizen_id": citizen_id,
        "digilocker_record_id": digilocker_record_id,
        "document_type": "community_certificate",
        "document_number": f"COM-{citizen_id[:8].upper()}",
        "document_name": "Community Certificate",
        "issue_date": _NOW - timedelta(days=365),
        "expiry_date": None,
        "verification_status": "verified",
        "verified_by": "Tahsildar Office",
        "verified_at": _NOW - timedelta(days=365),
        "download_url": f"{_BASE_URL}/community/{citizen_id}.pdf",
        "doc_metadata": metadata("caste_certificate", {
            "holder_name": full_name,
            "caste": profile.get("caste"),
            "community": profile.get("community"),
            "sub_caste": profile.get("sub_caste"),
            "religion": profile.get("religion"),
            "issuing_authority": "Revenue Department",
        }),
        "is_active": True,
    })

    # Residence Certificate
    docs.append({
        "citizen_id": citizen_id,
        "digilocker_record_id": digilocker_record_id,
        "document_type": "residence_certificate",
        "document_number": f"RES-{citizen_id[:8].upper()}",
        "document_name": "Residence Certificate",
        "issue_date": _NOW - timedelta(days=90),
        "expiry_date": _NOW + timedelta(days=275),
        "verification_status": "verified",
        "verified_by": "Village Administrative Officer",
        "verified_at": _NOW - timedelta(days=90),
        "download_url": f"{_BASE_URL}/residence/{citizen_id}.pdf",
        "doc_metadata": metadata("residence_certificate", {
            "holder_name": full_name,
            "village": village or first_land.get("village"),
            "taluk": taluk or first_land.get("taluk"),
            "district": district or first_land.get("district"),
            "state": state or first_land.get("state"),
        }),
        "is_active": True,
    })

    # Farmer-specific documents
    if profile.get("is_farmer"):
        docs.append({
            "citizen_id": citizen_id,
            "digilocker_record_id": digilocker_record_id,
            "document_type": "farmer_id",
            "document_number": profile.get("farmer_id", f"TN-FARMER-{citizen_id[:6].upper()}"),
            "document_name": "Farmer ID Card",
            "issue_date": _NOW - timedelta(days=365 * 2),
            "expiry_date": _NOW + timedelta(days=365 * 3),
            "verification_status": "verified",
            "verified_by": "Department of Agriculture",
            "verified_at": _NOW - timedelta(days=365 * 2),
            "download_url": f"{_BASE_URL}/farmer-id/{citizen_id}.pdf",
            "doc_metadata": metadata("farmer_id", {
                "farmer_id": profile.get("farmer_id"),
                "holder_name": full_name,
                "is_farmer": True,
                "occupation": profile.get("occupation"),
            }),
            "is_active": True,
        })
        # One land_record document per owned parcel so the enrichment pipeline
        # creates/updates each parcel individually. The existing aggregation
        # (sum of land_area) then yields the correct total (e.g. 2.5 + 1.0).
        for land in mock_land:
            docs.append({
                "citizen_id": citizen_id,
                "digilocker_record_id": digilocker_record_id,
                "document_type": "land_record",
                "document_number": land.get("patta_number") or land.get("survey_number"),
                "document_name": f"Land Record (Patta) - {land.get('survey_number')}",
                "issue_date": _NOW - timedelta(days=365 * 2),
                "expiry_date": None,
                "verification_status": "verified",
                "verified_by": "Revenue Department",
                "verified_at": _NOW - timedelta(days=365 * 2),
                "download_url": f"{_BASE_URL}/land-record/{citizen_id}.pdf",
                "doc_metadata": metadata("land_record", {
                    "owner_name": full_name,
                    "survey_number": land.get("survey_number"),
                    "land_area": land.get("land_area"),
                    "unit": land.get("land_area_unit"),
                    "land_type": land.get("land_type"),
                    "village": land.get("village"),
                    "taluk": land.get("taluk"),
                    "district": land.get("district"),
                    "state": land.get("state"),
                    "ownership_type": land.get("ownership_type"),
                    "patta_number": land.get("patta_number"),
                }),
                "is_active": True,
            })

    # Disability certificate
    if profile.get("is_disabled"):
        docs.append({
            "citizen_id": citizen_id,
            "digilocker_record_id": digilocker_record_id,
            "document_type": "disability_certificate",
            "document_number": f"DIS-{citizen_id[:8].upper()}",
            "document_name": "Disability Certificate",
            "issue_date": _NOW - timedelta(days=365),
            "expiry_date": _NOW + timedelta(days=365 * 4),
            "verification_status": "verified",
            "verified_by": "District Medical Board",
            "verified_at": _NOW - timedelta(days=365),
            "download_url": f"{_BASE_URL}/disability/{citizen_id}.pdf",
            "doc_metadata": metadata("disability_certificate", {
                "holder_name": full_name,
                "is_disabled": profile.get("is_disabled"),
                "disability_percentage": profile.get("disability_percentage") or 0,
            }),
            "is_active": True,
        })

    return docs
