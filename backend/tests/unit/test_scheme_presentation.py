"""Unit tests for the structured scheme presentation metadata layer.

The presentation layer must:
1. load the curated metadata correctly (all 23 catalogue scheme ids);
2. never return raw PDF extraction as a user-facing description;
3. reject obvious PDF/OCR noise;
4. mark source-poor schemes as needing manual review instead of inventing
   benefits.
"""
from types import SimpleNamespace

from app.services.scheme_presentation_service import (
    FALLBACK_DESCRIPTION,
    clean_benefit_bullets,
    get_presentation_by_scheme_id,
    is_extraction_noise,
    is_valid_presentation_text,
    load_scheme_presentation,
    presentation_for_scheme,
    resolve_presentation_for_scheme,
)


def test_presentation_metadata_loads_and_matches_catalogue():
    from app.services.eligibility_catalog_service import load_eligibility_catalogue

    entries = load_scheme_presentation()
    catalogue_ids = {entry.scheme_id for entry in load_eligibility_catalogue()}
    assert len(catalogue_ids) >= 20
    # Every catalogue scheme has a presentation entry keyed by the SAME id —
    # no second scheme identity system.
    assert set(entries) == catalogue_ids
    for entry in entries.values():
        assert entry["display_name"], "display_name must always be present"


def test_enam_presentation_is_clean_and_grounded():
    entry = get_presentation_by_scheme_id("enam")
    assert entry is not None
    assert "online" in entry["short_description"].lower()
    assert "Page No" not in entry["short_description"]
    assert "Uttam fasal" not in entry["short_description"]
    assert entry["benefits"]
    for bullet in entry["benefits"]:
        assert "Page No" not in bullet
        assert "Government of India" not in bullet


def test_smam_presentation_is_clean_and_grounded():
    entry = get_presentation_by_scheme_id("smam")
    assert entry is not None
    joined = " ".join(entry["benefits"])
    # Grounded in the SMAM 2025 guidelines (financial assistance pattern).
    assert "50%" in joined
    assert "40%" in joined
    assert "&TO&P" not in joined
    assert "F.No" not in joined


def test_raw_pdf_noise_is_rejected():
    assert is_extraction_noise(
        "Page No. 1 Uttam fasal Uttam Enam NATIONAL AGRICULTURE MARKET (e-NAM) "
        "A National Portal for eTrading..."
    )
    assert is_extraction_noise("&TO&P) - Part (8 | 29 | ) Government of India he")
    assert is_extraction_noise("Government of India")
    assert is_extraction_noise("Ministry of Agriculture & Farmers Welfare")
    assert is_extraction_noise("None")
    assert is_extraction_noise("")
    assert is_extraction_noise(None)
    assert is_extraction_noise("x" * 500)  # giant paragraph from PDF dump
    assert not is_extraction_noise("Income support of Rs. 6,000 per year.")


def test_noise_never_reaches_clean_bullets():
    cleaned = clean_benefit_bullets(
        [
            "Rs. 6,000 per year paid directly into the bank account",
            "Page No. 13 Benefits to Farmers",
            "www.enam.gov.in",
            None,
        ]
    )
    assert cleaned == ["Rs. 6,000 per year paid directly into the bank account"]


def test_review_required_schemes_use_safe_fallback():
    flagged = {
        sid for sid, entry in load_scheme_presentation().items() if entry["needs_review"]
    }
    # Source PDFs for these schemes do not contain clean scheme-benefit text.
    assert "pm-svanidhi" in flagged
    assert "pmksy" in flagged
    assert "pmuy" in flagged
    assert "post-matric-scholarship" in flagged
    assert "free-bus-travel-women-tn" in flagged


def test_benefits_needs_review_flag_present():
    pmmvy = get_presentation_by_scheme_id("pmmvy")
    assert pmmvy["benefits_needs_review"] is True
    assert pmmvy["short_description"]
    assert pmmvy["benefits"] == []


def test_presentation_for_scheme_unknown_scheme_is_fallback():
    result = presentation_for_scheme(None)
    assert result["short_description"] == FALLBACK_DESCRIPTION
    assert result["benefits"] == []
    assert result["needs_review"] is True


def test_presentation_for_scheme_resolves_by_catalogue_name():
    scheme = SimpleNamespace(scheme_name="e-NAM National Agriculture Market", scheme_id="")
    result = presentation_for_scheme(scheme)
    assert result["short_description"].startswith("e-NAM is an online")
    assert result["benefits"]


def test_presentation_for_scheme_needs_review_gets_fallback():
    scheme = SimpleNamespace(
        scheme_name="Pradhan Mantri Ujjwala Yojana", scheme_id="pmuy"
    )
    result = presentation_for_scheme(scheme)
    assert result["short_description"] == FALLBACK_DESCRIPTION
    assert result["benefits"] == []


def test_resolve_presentation_for_scheme_direct_id():
    scheme = SimpleNamespace(scheme_name="", scheme_id="pmay-g")
    entry = resolve_presentation_for_scheme(scheme)
    assert entry is not None
    assert entry["short_description"].startswith("PMAY-G gives financial help")



# ── Corrupted / mojibake hardening ──────────────────────────────────────────
# The exact broken OCR extraction that was surfacing under PMMVY's benefits.
CORRUPTED_PMMVY = (
    'Ei. {r*yr {qt, er6.q.qq. $ga rtP{s Dr. Rakesh Gupta, tAS Joint Secrotary '
    'Dt4^,,- Pgg"^\'ata*t\'tt*e 748.'
)
CORRUPTED_PMMVY_PAGE = (
    "Ei. {r*yr {qt, er6.q.qq. $ga rtP{s Dr. Rakesh Gupta eft-{ilr4tar "
    "Government of lndla Ministry of Women & Child Development"
)

TAMIL_SENTENCE = "இந்த திட்டம் விவசாயிகளுக்கு உதவுகிறது."
HINDI_SENTENCE = "यह योजना किसानों को आय सहायता देती है."


def test_corrupted_ocr_extraction_is_rejected():
    assert not is_valid_presentation_text(CORRUPTED_PMMVY)
    assert not is_valid_presentation_text(CORRUPTED_PMMVY_PAGE)
    assert not is_valid_presentation_text(
        "Page No. 1 Uttam fasal Uttam Enam NATIONAL AGRICULTURE MARKET (e-NAM)"
    )
    assert not is_valid_presentation_text(
        "&TO&P) - Part (8 | 29 | ) Government of India he"
    )
    assert not is_valid_presentation_text("N")
    assert not is_valid_presentation_text("Broken \ufffd encoding")


def test_legitimate_indian_language_unicode_is_not_rejected():
    # The validator must not treat non-ASCII Indian scripts as corruption.
    assert is_valid_presentation_text(TAMIL_SENTENCE)
    assert is_valid_presentation_text(HINDI_SENTENCE)
    assert is_valid_presentation_text(
        "Rs. 6,000 per year paid directly into the bank account."
    )
    assert is_valid_presentation_text(
        "Financial assistance of 50% of machine cost for SC/ST farmers."
    )
    assert is_valid_presentation_text("PMAY-U 2.0 (Housing for All — Urban)")


def test_corrupted_bullet_is_discarded_but_clean_bullet_kept():
    cleaned = clean_benefit_bullets(
        [
            CORRUPTED_PMMVY,
            CORRUPTED_PMMVY_PAGE,
            "Rs. 6,000 per year paid directly into the bank account",
            "N",
        ]
    )
    assert cleaned == ["Rs. 6,000 per year paid directly into the bank account"]


def test_pmmvy_corrupted_benefits_are_not_displayed():
    entry = get_presentation_by_scheme_id("pmmvy")
    assert entry is not None
    assert entry["benefits"] == []
    assert entry["benefits_needs_review"] is True

    scheme = SimpleNamespace(
        scheme_id="pmmvy",
        scheme_name="PMMVY (Pradhan Mantri Matru Vandana Yojana)",
        # Raw DB columns poisoned with the corrupted extraction.
        benefits=CORRUPTED_PMMVY,
        description=CORRUPTED_PMMVY_PAGE,
        eligibility_summary=CORRUPTED_PMMVY,
        required_documents=CORRUPTED_PMMVY,
        application_process=CORRUPTED_PMMVY,
    )
    result = presentation_for_scheme(scheme)
    assert result["benefits"] == []
    assert CORRUPTED_PMMVY not in result["short_description"]
    assert CORRUPTED_PMMVY not in (result["who_it_is_for"] or "")
    assert CORRUPTED_PMMVY not in (result["eligibility_summary"] or "")
    assert all(CORRUPTED_PMMVY not in item for item in result["documents"])
    assert all(CORRUPTED_PMMVY not in item for item in result["application"])


def test_raw_columns_are_never_a_presentation_fallback(monkeypatch):
    """When curated fields are unusable, nothing raw is substituted."""
    import app.services.scheme_presentation_service as presentation_module

    corrupted_entry = {
        "display_name": CORRUPTED_PMMVY,
        "short_description": CORRUPTED_PMMVY,
        "benefits": [CORRUPTED_PMMVY, "Rs. 6,000 per year", "N"],
        "needs_review": False,
        "benefits_needs_review": False,
        "source_document": "x.pdf",
        "who_it_is_for": CORRUPTED_PMMVY,
        "eligibility_summary": CORRUPTED_PMMVY,
        "documents": [CORRUPTED_PMMVY, "Land ownership / land record"],
        "application": [CORRUPTED_PMMVY, "Visit the official portal."],
    }
    monkeypatch.setattr(
        presentation_module,
        "resolve_presentation_for_scheme",
        lambda scheme: corrupted_entry,
    )
    scheme = SimpleNamespace(
        scheme_id="enam",
        scheme_name="e-NAM",
        benefits=CORRUPTED_PMMVY,
        description=CORRUPTED_PMMVY,
    )
    result = presentation_module.presentation_for_scheme(scheme)
    assert result["display_name"] is None
    assert result["short_description"] == presentation_module.FALLBACK_DESCRIPTION
    # The entry is unusable, so it is treated as needing review and the
    # corrupted bullets are dropped — the raw DB `benefits` is never used.
    assert result["benefits"] == []
    assert result["needs_review"] is True
    assert result["who_it_is_for"] is None
    assert result["eligibility_summary"] is None
    assert result["documents"] == ["Land ownership / land record"]
    assert result["application"] == ["Visit the official portal."]


def test_valid_curated_benefits_keep_clean_bullets_only(monkeypatch):
    import app.services.scheme_presentation_service as presentation_module

    entry = {
        "display_name": "e-NAM (National Agriculture Market)",
        "short_description": (
            "e-NAM is an online national market platform for farmers."
        ),
        "benefits": [
            CORRUPTED_PMMVY,
            "Online access to more buyers and markets",
            "Page No. 13",
            "N",
        ],
        "needs_review": False,
        "benefits_needs_review": False,
        "source_document": "x.pdf",
        "who_it_is_for": None,
        "eligibility_summary": None,
        "documents": [],
        "application": [],
    }
    monkeypatch.setattr(
        presentation_module,
        "resolve_presentation_for_scheme",
        lambda scheme: entry,
    )
    result = presentation_module.presentation_for_scheme(
        SimpleNamespace(scheme_id="enam", scheme_name="e-NAM")
    )
    assert result["benefits"] == ["Online access to more buyers and markets"]


def test_all_catalogue_schemes_are_clean_or_safely_reviewed():
    from app.services.eligibility_catalog_service import load_eligibility_catalogue

    catalogue_ids = {entry.scheme_id for entry in load_eligibility_catalogue()}
    entries = load_scheme_presentation()
    assert set(entries) == catalogue_ids
    assert len(catalogue_ids) == 23

    for scheme_id in sorted(catalogue_ids):
        result = presentation_for_scheme(
            SimpleNamespace(scheme_id=scheme_id, scheme_name="")
        )
        # A citizen always gets safe text — never raw extraction.
        assert result["short_description"]
        assert is_valid_presentation_text(result["short_description"])
        for bullet in result["benefits"]:
            assert is_valid_presentation_text(bullet)
        for document in result["documents"]:
            assert is_valid_presentation_text(document)
        for step in result["application"]:
            assert is_valid_presentation_text(step)
        if result["who_it_is_for"] is not None:
            assert is_valid_presentation_text(result["who_it_is_for"])
        if result["eligibility_summary"] is not None:
            assert is_valid_presentation_text(result["eligibility_summary"])


def test_review_commentary_is_not_exposed_as_citizen_content():
    """Source-quality notes belong in the flags, not in citizen-facing text."""
    forbidden = (
        "supplied source",
        "manual review",
        "source pdf",
        "on disk",
        "needs review",
    )
    for scheme_id, entry in load_scheme_presentation().items():
        fields = [
            entry["short_description"],
            entry["who_it_is_for"],
            entry["eligibility_summary"],
            *entry["benefits"],
            *entry["documents"],
            *entry["application"],
        ]
        for value in fields:
            lowered = (value or "").lower()
            for marker in forbidden:
                assert marker not in lowered, f"{scheme_id}: {value!r}"


def test_eligibility_summary_review_flag_is_exposed():
    result = presentation_for_scheme(
        SimpleNamespace(scheme_id="pmksy", scheme_name="")
    )
    assert result["eligibility_summary_needs_review"] is True
    # Unsupported content is withheld rather than invented.
    assert result["eligibility_summary"] in (None, "")