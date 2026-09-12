# Eligibility Extraction Plan - Government Schemes

## Phase: Foundation Building (Non-Breaking)

This document outlines the systematic extraction of eligibility criteria from 24+ government scheme PDFs into a structured, machine-evaluable catalogue.

---

## STEP 1: SCHEME DISCOVERY

### Schemes Identified from PDF Files (24 schemes)

| # | Scheme Name | PDF Filename | Scheme ID (To Assign) | Beneficiary Scope | Status |
|---|------------|--------------|----------------------|-------------------|--------|
| 1 | PM-KISAN | PM-KISAN_Operational_Guidelines.pdf | pm-kisan | INDIVIDUAL | ✓ Rules Exist |
| 2 | PM-KUSUM | PM-KUSUM_Guidelines.pdf | pm-kusum | MULTI_LEVEL | ✓ Rules Exist |
| 3 | PMFBY | PMFBY_Scheme_Document.pdf | pmfby | INDIVIDUAL | ✓ Rules Exist |
| 4 | PM-RKVY / PKVY | PM-RKVY_and_PKVY_Guidelines.pdf | pm-rkvy-pkvy | MULTI_LEVEL | ✓ Rules Exist |
| 5 | PMFME | PMFME_Scheme_Guidelines.pdf | pmfme | INDIVIDUAL | ✓ Rules Exist |
| 6 | SMAM | SMAM_Operational_Guidelines_2025.pdf | smam | INDIVIDUAL | ✓ Rules Exist |
| 7 | MIDH | MIDH_Operational_Guidelines_2025.pdf | midh | MULTI_LEVEL | ✓ Rules Exist |
| 8 | PM-SVANidhi | PM_Street_Vendor_AtmaNirbhar_Nidhi_PM_SVANidhi_3.pdf | pm-svanidhi | INDIVIDUAL | ❌ Rules Missing |
| 9 | PM Vishwakarma | PM_Vishwakarma_Yojana.pdf | pm-vishwakarma | INDIVIDUAL | ❌ Rules Missing |
| 10 | PMAY-U | Pradhan_Mantri_Awas_Yojana_-_Urban_PMAY-U_2.pdf | pmay-u | INDIVIDUAL | ❌ Rules Missing |
| 11 | PM-JDY | Pradhan_Mantri_Jan_Dhan_Yojana_PMJDY_3.pdf | pm-jdy | INDIVIDUAL | ❌ Rules Missing |
| 12 | PMKSY | Pradhan_Mantri_Krishi_Sinchayee_Yojana_PMKSY_2.pdf | pm-ksy | INDIVIDUAL | ❌ Rules Missing |
| 13 | PMMVY | Pradhan_Mantri_Matru_Vandana_Yojana_PMMVY.pdf | pm-mvy | INDIVIDUAL | ❌ Rules Missing |
| 14 | PM-UJY | Pradhan_Mantri_Ujjwala_Yojana_PMUY.pdf | pm-ujy | INDIVIDUAL | ❌ Rules Missing |
| 15 | Free Bus Travel (Women-TN) | Free_Bus_Travel_Scheme_for_Women_TN_Government_Buses.pdf | free-bus-tn | INDIVIDUAL | ❌ Rules Missing |
| 16 | e-NAM | e-NAM_National_Agriculture_Market_3.pdf | e-nam | INDIVIDUAL | ❌ Rules Missing |
| 17 | Jal Jeevan Mission | Jal_Jeevan_Mission.pdf | jjm | COMMUNITY | ❌ Rules Missing |
| 18 | NFSA / PDS | National_Food_Security_Act_-_Public_Distribution_System_2.pdf | nfsa-pds | INDIVIDUAL | ❌ Rules Missing |
| 19 | NSP | National_Scholarship_Portal_-_Post_Matric_Scholarship_SCSTOBC_2.pdf | nsp-scholarship | INDIVIDUAL | ❌ Rules Missing |
| 20 | PMAY-G | PMAY-G_Guidelines.pdf | pmay-g | INDIVIDUAL | ❌ Rules Missing |
| 21 | Swachh Bharat Mission | Swachh_Bharat_Mission_-_Gramin.pdf | sbm-g | INDIVIDUAL | ❌ Rules Missing |
| 22 | UPIS | Unified_Package_Insurance_Scheme_Guidelines.pdf | upis | INDIVIDUAL | ❌ Rules Missing |
| 23 | Saksham Anganwadi | Saksham_Anganwadi_Poshan_2.0_Guidelines.pdf | saksham | INSTITUTION | ❌ Rules Missing |
| 24 | UPIS / Raita Bandhu | (Variant/Similar to UPIS) | - | INDIVIDUAL | TBD |

---

## STEP 2: CITIZEN PROFILE FIELDS AVAILABLE

### From CitizenProfile Model

#### Personal Information
- ✓ id, citizen_id
- ✓ father_name, mother_name
- ✓ occupation
- ✓ marital_status
- ✓ blood_group
- ✓ nationality

#### Economic Information
- ✓ annual_income
- ✓ income_category (BPL, APL, EWS, LIG, MIG, HIG)

#### Social Classification
- ✓ caste
- ✓ community
- ✓ sub_caste
- ✓ religion

#### Health & Disability
- ✓ is_disabled
- ✓ disability_type
- ✓ disability_percentage

#### Agriculture & Land
- ✓ is_farmer
- ✓ farmer_id
- (Land records in separate LandRecord table)

#### Education
- ✓ education_level
- ✓ education_institution

#### Family
- ✓ family_member_count
- ✓ family_details (JSON)

#### Timestamps
- ✓ profile_completion_percentage
- ✓ sync_status (DigiLocker)
- ✓ last_synced_at
- ✓ created_at, updated_at

### From LandRecord Model

- ✓ id, citizen_id
- ✓ survey_number, land_area, land_area_unit
- ✓ land_type (AGRICULTURAL, RESIDENTIAL, COMMERCIAL, FOREST, WASTELAND)
- ✓ village, taluk, district, state
- ✓ ownership_type
- ✓ patta_number
- ✓ created_at, updated_at

---

## STEP 3: ELIGIBILITY EXTRACTION FRAMEWORK

### Eligibility Criterion Categories

#### A. Basic Eligibility (Demographic)
- age, age_min, age_max
- gender
- citizenship
- marital_status
- residence (state/district/rural/urban)

#### B. Financial Criteria
- annual_income, annual_income_max
- monthly_income, monthly_income_max
- household_income, household_income_max
- income_category
- income_tax_payer (exclusion)
- debt_status, loan_status

#### C. Land/Agriculture Criteria
- land_required (boolean)
- land_type (agricultural, cultivable, barren, etc.)
- land_area_min, land_area_max
- ownership_type (owned, leased, tenant, etc.)
- farmer_category (small, marginal, large)
- crop_type, crop_area
- cultivated_area_min

#### D. Social/Category Criteria
- SC, ST, OBC, EWS
- minority (religion-based)
- women (gender)
- disability (is_disabled, disability_percentage)
- widow, senior_citizen
- priority_group

#### E. Employment Criteria
- government_employee (exclusion typical)
- private_employee
- self_employed
- unemployed
- informal_worker
- artisan
- agricultural_worker

#### F. Enterprise/Business Criteria
- enterprise_type
- existing_enterprise, new_enterprise
- number_of_employees
- annual_turnover
- ownership_type
- business_activity
- micro/small_classification
- food_processing, traditional_trade

#### G. Housing Criteria
- house_ownership
- house_type (pucca, kutcha)
- homelessness
- previous_housing_benefit

#### H. Banking/Document Criteria
- aadhaar_required
- bank_account_required
- land_record_required
- caste_certificate_required
- income_certificate_required
- business_registration_required
- farmer_id_required

#### I. Previous Benefit/Loan Conditions
- previous_government_assistance (exclusion)
- previous_loan (exclusion)
- duplicate_benefit_check

#### J. Scheme-Specific Conditions
- any scheme-specific restrictions

---

## STEP 4: RULE TYPE CLASSIFICATION

Each rule extracted must be classified as:

- **REQUIRED**: Mandatory positive criterion
- **EXCLUSION**: Grounds for disqualification
- **CONDITIONAL**: IF X THEN Y applies
- **ONE_OF**: Choose one from a list
- **ANY_OF**: Satisfy any one condition
- **ALL_OF**: Satisfy all conditions
- **THRESHOLD**: Value must be >= or <=
- **DOCUMENT_REQUIRED**: Evidence/proof required
- **EVIDENCE_REQUIRED**: Verification needed
- **PROGRAM_LEVEL**: Scheme-wide program constraint
- **SCHEME_SPECIFIC**: Custom constraint for this scheme

---

## STEP 5: EXISTING RULES TO PRESERVE

### Currently Defined Eligibility Rules (7 schemes)

✓ PM-KISAN
- Landholding farmer families
- Cultivable land required
- Income tax payers excluded
- Government employees excluded
- Pensioners excluded
- Constitutional post holders excluded

✓ PM-KUSUM
- Farmers, farmer groups, FPOs, panchayats, water user associations
- Land required (barren, uncultivable, or agricultural)
- Owned or leased land
- Solar power/pump installation activities

✓ PMFBY
- Farmers (not yet fully extracted from code)

✓ PM-RKVY / PKVY
- Small/marginal farmers, FPOs, SHGs, cooperatives
- Agricultural land required
- Organic farming activities
- PGS certification where required

✓ PMFME
- Existing micro food processing entrepreneurs
- < 10 workers
- Age >= 18
- Minimum 8th standard education
- One beneficiary per family
- ODOP preference

✓ SMAM
- Small/marginal farmers
- SC/ST/women/NE farmers
- FRA patta holders
- Land required
- Mechanization/machinery activities

✓ MIDH
- Horticulture farmers
- FPOs, SHGs, PRIs
- Horticulture activity mandatory
- Land required (horticulture or agricultural)

---

## STEP 6: MISSING RULES

The following 17 schemes need eligibility extraction from PDFs:

1. PM-SVANidhi (Street vendors)
2. PM Vishwakarma (Artisans)
3. PMAY-U (Urban housing)
4. PM-JDY (Jan Dhan - banking)
5. PMKSY (Crop insurance / irrigation)
6. PMMVY (Maternity benefit)
7. PM-UJY (LPG connection)
8. Free Bus Travel (Women-TN)
9. e-NAM (Agricultural market)
10. Jal Jeevan Mission (Water)
11. NFSA / PDS (Food security)
12. NSP (Scholarships)
13. PMAY-G (Rural housing)
14. Swachh Bharat Mission (Sanitation)
15. UPIS (Insurance scheme)
16. Saksham Anganwadi (Nutrition)
17. Others

---

## STEP 7: EXTRACTION STRATEGY

For each missing scheme:

1. **Locate PDF** in backend/data/
2. **Read eligibility section** (usually in first 2-5 pages)
3. **Extract criteria** into structured format
4. **Classify rule types**
5. **Identify excluded groups** (if any)
6. **Determine beneficiary scope** (INDIVIDUAL, FAMILY, ENTERPRISE, etc.)
7. **Map to citizen profile fields**
8. **Flag missing profile fields**
9. **Add source traceability** (page, section)
10. **Compare against existing rules** (if any)

---

## STEP 8: OUTPUT STRUCTURE

### Option A: JSON Files (Per Scheme)

```
data/eligibility_rules/
  ├── pm_kisan.json
  ├── pm_kusum.json
  ├── pmfby.json
  ├── pm_svanidhi.json
  ├── pm_vishwakarma.json
  └── ... (24 total)
```

### Option B: Python Module (One File)

```python
# app/models/scheme_eligibility_rules.py
# Contains all 24 schemes + registry
```

### Decision: Use Python module (`app/models/scheme_eligibility_rules_extended.py`)

- Consistent with existing `scheme_rules.py`
- Type-safe with Pydantic
- Easy to version control
- Easy to test and validate
- Single source of truth

---

## STEP 9: VALIDATION TESTS

Create `tests/unit/test_eligibility_catalogue.py`:

1. Every scheme has a unique scheme_id ✓
2. Every scheme has a scheme_name ✓
3. Every scheme has beneficiary_scope ✓
4. Every rule has source reference ✓
5. Every operator is valid (>=, <=, ==, in, etc.) ✓
6. No duplicate rules per scheme ✓
7. Conditional rules have both when & require ✓
8. No unknown profile fields referenced ✓
9. Exclusion rules are distinct from required rules ✓

---

## STEP 10: SAMPLE EVALUATION

Create synthetic citizen profiles to test eligibility evaluation:

```python
# tests/fixtures/synthetic_citizens.py
citizen_farmer_eligible_pm_kisan = CitizenProfile(...)
citizen_artisan_not_eligible_pm_kisan = CitizenProfile(...)
citizen_partial_info = CitizenProfile(...)  # INSUFFICIENT_INFORMATION
```

---

## STEP 11: DELIVERABLES

1. ✓ Extended scheme eligibility rules file (24 schemes)
2. ✓ Validation tests
3. ✓ Sample evaluation tests
4. ✓ Scheme-to-citizen-profile mapping documentation
5. ✓ Missing profile fields list
6. ✓ Beneficiary scope classification
7. ✓ Implementation report

---

## STEP 12: EXECUTION CHECKLIST

- [ ] Create scheme discovery inventory
- [ ] Extract eligibility from PM-SVANidhi
- [ ] Extract eligibility from PM Vishwakarma
- [ ] Extract eligibility from PMAY-U
- [ ] Extract eligibility from PM-JDY
- [ ] Extract eligibility from PMKSY
- [ ] Extract eligibility from PMMVY
- [ ] Extract eligibility from PM-UJY
- [ ] Extract eligibility from Free Bus Travel (Women-TN)
- [ ] Extract eligibility from e-NAM
- [ ] Extract eligibility from Jal Jeevan Mission
- [ ] Extract eligibility from NFSA / PDS
- [ ] Extract eligibility from NSP
- [ ] Extract eligibility from PMAY-G
- [ ] Extract eligibility from Swachh Bharat Mission
- [ ] Extract eligibility from UPIS
- [ ] Extract eligibility from Saksham Anganwadi
- [ ] Compile all into extended scheme eligibility rules file
- [ ] Add validation tests
- [ ] Add synthetic test citizens
- [ ] Run all tests
- [ ] Generate final report

---

## CONSTRAINTS & RULES

✓ PDF/document is source of truth
✓ Do not invent eligibility criteria
✓ Mark ambiguous/unclear items as REQUIRES_MANUAL_REVIEW
✓ Preserve existing 7 schemes exactly
✓ Do NOT modify recommendation logic yet
✓ Every extracted rule must be traceable to source PDF
✓ Distinguish NOT_ELIGIBLE from INSUFFICIENT_INFORMATION
✓ Do not assume every scheme is individual-citizen
✓ No changes to RAG, authentication, voice, document upload, profile UI

---

## Success Criteria

1. ✓ All 24 schemes have structured eligibility rules
2. ✓ All rules are traceable to source PDF
3. ✓ All rules can be evaluated against citizen profiles
4. ✓ System correctly identifies: ELIGIBLE, POTENTIALLY_ELIGIBLE, NOT_ELIGIBLE, INSUFFICIENT_INFORMATION
5. ✓ Existing 7 schemes' rules remain unchanged
6. ✓ No breaking changes to existing APIs/services
7. ✓ Validation tests pass
8. ✓ Sample evaluation tests demonstrate correct behavior

