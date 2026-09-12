# Quick Reference Guide - 5 Schemes Eligibility Rules
## Lookup Table for Backend Implementation

---

## SCHEME ELIGIBILITY MATRIX

### 1. PMJDY - Pradhan Mantri Jan Dhan Yojana
**Type:** Banking | **Pages:** 1 | **Confidence:** HIGH ✅

**Core Rules:**
```
IF age >= 18 AND age <= 65 
   AND nationality == 'INDIAN' 
   AND aadhar_number IS NOT NULL 
   AND mobile_number IS NOT NULL 
   AND existing_bank_account == FALSE
THEN eligible = TRUE
```

**Priority Fields:**
- age (18-65) - REQUIRED
- nationality - REQUIRED
- aadhar_number - REQUIRED (JAM linkage)
- mobile_number - REQUIRED (JAM linkage)
- location_type - PREFERENCE (rural 59%)

**Exclusions:**
- Existing functional bank account

**Benefits:**
- Jan Dhan Account, RuPay Card, ₹10k OD, Insurance, DBT access

---

### 2. PMKSY - Pradhan Mantri Krishi Sinchayee Yojana
**Type:** Agriculture | **Pages:** 19 | **Confidence:** MEDIUM 🟡

**Core Rules:**
```
IF is_farmer == TRUE 
   AND farmer_id IS NOT NULL 
   AND land_area > 0 
   AND land_type == 'AGRICULTURAL' 
   AND ownership_type IN ['OWNED', 'LEASED'] 
   AND location_type == 'RURAL' 
   AND state.pmksy_enabled == TRUE
THEN check_state_specific_variations()
```

**Priority Fields:**
- is_farmer - REQUIRED
- farmer_id - REQUIRED
- land_area - REQUIRED (varies by state)
- land_type - REQUIRED (AGRICULTURAL only)
- ownership_type - REQUIRED (OWNED or LEASED)
- state - REQUIRED (state-specific variations)
- district - REQUIRED (irrigation plan)
- village - REQUIRED (village assessment)

**Exclusions:**
- Non-farmer status
- Non-agricultural land
- Wasteland/Forest land
- Outside irrigation command area

**State-Specific Variables:**
- Income ceiling (NOT found - TO VERIFY)
- Land size requirements (NOT found - TO VERIFY)
- Irrigation command areas (state-dependent)

**Benefits:**
- Crop insurance, Irrigation subsidies, Yield improvement

---

### 3. PMUY - Pradhan Mantri Ujjwala Yojana
**Type:** Energy/LPG | **Pages:** 13 | **Confidence:** HIGH ✅

**Core Rules:**
```
IF income_category == 'BPL' 
   AND annual_income <= bpl_threshold 
   AND existing_lpg_connection == FALSE 
   AND (identity_document IS NOT NULL 
        OR address_proof IS NOT NULL)
THEN eligible = TRUE
```

**Priority Fields:**
- income_category - REQUIRED (BPL ONLY)
- annual_income - REQUIRED (≤ BPL threshold)
- existing_lpg_connection - EXCLUSION (must be false)
- identity_document - REQUIRED
- address_proof - CONDITIONAL (except FTL customers)
- gender - PREFERENCE (women prioritized)

**Exclusions:**
- APL (Above Poverty Line) status
- Existing LPG connection in household
- Income exceeds BPL limit
- Already received subsidy under scheme

**Geographic:**
- National (both rural & urban eligible)

**Document Requirements:**
- Identity proof (Aadhaar, PAN, Voter ID)
- Address proof (except FTL)
- Income certificate (BPL proof)
- 47 document types tracked

**Benefits:**
- Free LPG connection, Waived deposit, Insurance

---

### 4. ENAM - e-NAM (National Agriculture Market)
**Type:** Agricultural Trade Platform | **Pages:** 188 | **Confidence:** MEDIUM 🟡

**Core Rules:**
```
IF (is_farmer == TRUE OR occupation == 'TRADER')
   AND state.marketing_reforms_compliant == TRUE 
   AND state.enam_enabled == TRUE 
   AND enam_mandi_registration == TRUE 
   AND (digital_access == TRUE 
        OR mobile_app_available == TRUE)
THEN eligible = TRUE
ELSE IF state NOT IN marketing_reform_states
     THEN ineligible_reason = "State lacks 3 mandatory reforms"
```

**Priority Fields:**
- is_farmer OR occupation='TRADER' - REQUIRED
- state - REQUIRED (marketing reforms dependent)
- enam_mandi_registration - REQUIRED
- enam_portal_user_id - REQUIRED
- digital_access - REQUIRED (internet/mobile)

**Mandatory State Prerequisites (ALL 3 REQUIRED):**
1. Removal of trade restrictions and middlemen restrictions
2. Single point tax collection system
3. Level playing field for traders (no internal levies)

**Exclusions:**
- States without 3 mandatory marketing reforms
- Non-registered farmers/traders
- Unauthorized commodity types
- Non-notified mandis
- Fraud/default history

**Authorized Commodities:**
- Raw cashew nuts, Agricultural products (28+ types)
- See PDF pages 14-27 for complete list

**Benefits:**
- Direct market access, Price discovery, National reach, Transparency, Lower costs

**Document Burden:** Heavy (84 types)

---

### 5. JJM - Jal Jeevan Mission
**Type:** Water Supply Infrastructure | **Pages:** 96 | **Confidence:** MEDIUM-HIGH 🟡✅

**Core Rules:**
```
IF location_type == 'RURAL' 
   AND state.jjm_enabled == TRUE 
   AND village IN jjm_target_villages 
   AND water_access_status != 'SAFE_DRINKING_WATER' 
   AND gram_panchayat_participation == TRUE 
   AND community_willing_to_participate == TRUE
THEN eligible = TRUE
```

**Priority Fields:**
- location_type - REQUIRED (RURAL ONLY)
- state - REQUIRED (JJM enabled state)
- district - REQUIRED (JJM active district)
- village - REQUIRED (specific village list)
- water_access_status - REQUIRED (without safe water)
- gram_panchayat_participation - REQUIRED
- community_participation - CONDITIONAL (required for success)

**Exclusions:**
- Urban areas (rural-only scheme)
- Villages with existing safe water supply
- Non-participatory communities
- Communities unwilling to manage systems

**Implementation Framework:**
- Village Water Committee (elected)
- Nal Jal Mitras (trained operators)
- Tariff collection system
- Operation & maintenance fund

**Community Requirements:**
- Female representation: ≥50% in committee
- Gram Panchayat approval required
- Community willingness to contribute
- Water quality monitoring commitment

**Benefits:**
- Individual household water connection
- Health improvement (reduced water-borne disease)
- Time savings (especially women)
- Sanitation linkage
- Government infrastructure + training

**Document Burden:** Very Heavy (245 types)

---

## 🗂️ QUICK LOOKUP: By Criterion Type

### Age Requirements
| Scheme | Requirement | Type |
|--------|-------------|------|
| PMJDY | 18-65 years | REQUIRED |
| PMKSY | None specified | NOT REQUIRED |
| PMUY | Not specified | NOT REQUIRED |
| ENAM | Not specified | NOT REQUIRED |
| JJM | All ages | NOT REQUIRED |

### Geographic Scope
| Scheme | Urban | Rural | National | State-Based |
|--------|-------|-------|----------|------------|
| PMJDY | ✅ | ✅ (59%) | ✅ | No |
| PMKSY | ❌ | ✅ | NO | YES |
| PMUY | ✅ | ✅ | ✅ | Possible |
| ENAM | ❌ | ✅ | NO | YES (reforms) |
| JJM | ❌ | ✅ | NO | YES |

### Income Requirements
| Scheme | Limit | Type | Notes |
|--------|-------|------|-------|
| PMJDY | None | NO LIMIT | All income classes |
| PMKSY | State-var | STATE SPECIFIC | Not found in PDF |
| PMUY | BPL | SECC BASED | BPL ONLY |
| ENAM | None | NO LIMIT | All farmers/traders |
| JJM | None | NO LIMIT | All rural households |

### Occupational Focus
| Scheme | Farmer | Trader | General | Notes |
|--------|--------|--------|---------|-------|
| PMJDY | ✅ | ✅ | ✅ | All adults |
| PMKSY | ✅ (ONLY) | ❌ | ❌ | Farmer exclusive |
| PMUY | ✅ | ✅ | ✅ | BPL households |
| ENAM | ✅ (PRIMARY) | ✅ (PRIMARY) | ❌ | Ag sector only |
| JJM | ✅ | ✅ | ✅ | All rural |

### Gender Preferences
| Scheme | Requirement | Level | Notes |
|--------|-------------|-------|-------|
| PMJDY | Both | PREFERENCE | 53% women account holders |
| PMKSY | Both | NOT SPECIFIED | No preference stated |
| PMUY | Female | PREFERENCE | Women prioritized for benefits |
| ENAM | Both | NOT SPECIFIED | No preference stated |
| JJM | All | NEUTRAL | Female representation in committees |

### Digital Requirements
| Scheme | Aadhar | Mobile | Portal | Internet |
|--------|--------|--------|--------|----------|
| PMJDY | ✅ REQ | ✅ REQ | ✅ | Optional |
| PMKSY | Optional | Optional | No | No |
| PMUY | ✅ | Optional | No | No |
| ENAM | Optional | Optional | ✅ REQ | ✅ REQ |
| JJM | No | No | No | No |

### Key Exclusion Criteria
| Scheme | Primary Exclusion |
|--------|-------------------|
| PMJDY | Existing bank account |
| PMKSY | Non-agricultural land, Wasteland |
| PMUY | APL status, Existing LPG |
| ENAM | Non-reforming states |
| JJM | Urban areas, Existing water supply |

---

## 🔧 DATABASE FIELDS REQUIRED PER SCHEME

### PMJDY Required Fields
```json
{
  "age": "integer (18-65)",
  "nationality": "string (INDIAN)",
  "aadhar_number": "string (NOT NULL)",
  "mobile_number": "string (NOT NULL)",
  "location_type": "enum (RURAL/URBAN) [PREFERENCE]",
  "existing_bank_account": "boolean (false)"
}
```

### PMKSY Required Fields
```json
{
  "is_farmer": "boolean (true)",
  "farmer_id": "string (NOT NULL)",
  "occupation": "string (FARMER)",
  "land_area": "decimal (> 0)",
  "land_type": "enum (AGRICULTURAL)",
  "ownership_type": "enum (OWNED|LEASED)",
  "state": "string (pmksy_enabled)",
  "district": "string",
  "village": "string",
  "location_type": "enum (RURAL)",
  "irrigation_status": "enum (CANAL|IRRIGATED|RAINFED) [CONDITIONAL]"
}
```

### PMUY Required Fields
```json
{
  "income_category": "enum (BPL)",
  "annual_income": "decimal (<= bpl_threshold)",
  "identity_document": "string (NOT NULL)",
  "address_proof": "string [CONDITIONAL]",
  "existing_lpg_connection": "boolean (false)",
  "gender": "enum (MALE|FEMALE) [PREFERENCE]",
  "location_type": "enum (RURAL|URBAN) [OPTIONAL]"
}
```

### ENAM Required Fields
```json
{
  "occupation": "enum (FARMER|TRADER)",
  "is_farmer": "boolean [FOR FARMER CATEGORY]",
  "farmer_id": "string [FOR FARMER CATEGORY]",
  "trader_license_number": "string [FOR TRADER CATEGORY]",
  "state": "string (marketing_reforms_compliant)",
  "enam_mandi_registration": "boolean (true)",
  "enam_portal_user_id": "string (NOT NULL)",
  "digital_access": "boolean (true)",
  "authorized_commodity_types": "array"
}
```

### JJM Required Fields
```json
{
  "location_type": "enum (RURAL)",
  "state": "string (jjm_enabled)",
  "district": "string (jjm_active)",
  "village": "string (in_target_list)",
  "water_access_status": "enum (WITHOUT_SAFE_WATER)",
  "gram_panchayat_participation": "boolean (true)",
  "community_participation": "boolean [CONDITIONAL]",
  "family_member_count": "integer (> 0)"
}
```

---

## ✅ VALIDATION QUERY TEMPLATES

### SQL-Style Validation Rules

#### PMJDY Eligibility Check
```sql
SELECT citizen_id, 'PMJDY_ELIGIBLE' as scheme
FROM citizen_profile cp
WHERE cp.age >= 18 
  AND cp.age <= 65
  AND cp.nationality = 'INDIAN'
  AND cp.aadhar_number IS NOT NULL
  AND cp.mobile_number IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM bank_accounts ba 
    WHERE ba.citizen_id = cp.id AND ba.active = true
  )
```

#### PMKSY Eligibility Check
```sql
SELECT cp.citizen_id, 'PMKSY_ELIGIBLE' as scheme, lr.land_area
FROM citizen_profile cp
JOIN land_records lr ON cp.id = lr.citizen_id
WHERE cp.is_farmer = true
  AND cp.farmer_id IS NOT NULL
  AND lr.land_area > 0
  AND lr.land_type = 'AGRICULTURAL'
  AND lr.ownership_type IN ('OWNED', 'LEASED')
  AND cp.location_type = 'RURAL'
  AND lr.state IN (SELECT state FROM pmksy_enabled_states)
```

#### PMUY Eligibility Check
```sql
SELECT cp.citizen_id, 'PMUY_ELIGIBLE' as scheme
FROM citizen_profile cp
WHERE cp.income_category = 'BPL'
  AND cp.annual_income <= (
    SELECT bpl_threshold FROM state_income_limits 
    WHERE state_code = cp.state
  )
  AND NOT EXISTS (
    SELECT 1 FROM household_infrastructure hi
    WHERE hi.citizen_id = cp.id 
    AND hi.existing_lpg_connection = true
  )
  AND (cp.aadhar_number IS NOT NULL 
       OR cp.identity_document IS NOT NULL)
```

#### ENAM Eligibility Check
```sql
SELECT cp.citizen_id, 'ENAM_ELIGIBLE' as scheme
FROM citizen_profile cp
WHERE (cp.is_farmer = true OR cp.occupation = 'TRADER')
  AND cp.state IN (
    SELECT state FROM enam_states 
    WHERE marketing_reforms_compliant = true
  )
  AND cp.enam_portal_user_id IS NOT NULL
  AND cp.enam_mandi_registration = true
  AND (cp.mobile_number IS NOT NULL 
       OR cp.digital_access = true)
```

#### JJM Eligibility Check
```sql
SELECT cp.citizen_id, 'JJM_ELIGIBLE' as scheme
FROM citizen_profile cp
JOIN household_infrastructure hi ON cp.id = hi.citizen_id
WHERE cp.location_type = 'RURAL'
  AND cp.state IN (SELECT state FROM jjm_enabled_states)
  AND cp.district IN (SELECT district FROM jjm_active_districts)
  AND cp.village IN (SELECT village FROM jjm_target_villages)
  AND hi.water_access_status != 'SAFE_DRINKING_WATER'
  AND EXISTS (
    SELECT 1 FROM gram_panchayat_participation gp
    WHERE gp.village = cp.village AND gp.status = 'APPROVED'
  )
```

---

## 📊 IMPLEMENTATION PRIORITY MATRIX

### By Complexity (Easy to Hard)
1. **PMJDY** - Simple age/citizenship/digital checks
2. **PMUY** - Income category based, straightforward
3. **PMKSY** - Multi-field land validation, state-specific
4. **JJM** - Community participation, geographic targeting
5. **ENAM** - State reforms prerequisite, complex validation

### By Impact (High to Low)
1. **PMKSY** - 150+ million farmers affected
2. **ENAM** - 1000+ mandis across India
3. **JJM** - 190 million rural people targeted
4. **PMJDY** - 32+ crore account holders
5. **PMUY** - 50+ million LPG connections

### By Data Requirements
1. **PMJDY** - Minimal (age, ID, mobile)
2. **PMUY** - Moderate (income + LPG status)
3. **PMKSY** - Heavy (land records + farmer data)
4. **ENAM** - Heavy (trader/mandi registration)
5. **JJM** - Very Heavy (village-level + community)

---

## 🚀 IMPLEMENTATION ROADMAP

### Sprint 1: Core Infrastructure
- [ ] Add new database fields (4 hours)
- [ ] Create state configuration tables (2 hours)
- [ ] Implement JSON rule loader (3 hours)
- [ ] Basic rule engine (4 hours)

### Sprint 2: PMJDY & PMUY Integration
- [ ] PMJDY evaluation logic (3 hours)
- [ ] PMUY evaluation logic (4 hours)
- [ ] Validation tests (3 hours)
- [ ] Documentation (2 hours)

### Sprint 3: Agricultural Schemes (PMKSY & ENAM)
- [ ] PMKSY complex rules (4 hours)
- [ ] ENAM state validation (4 hours)
- [ ] State-specific tests (3 hours)
- [ ] Integration with land records (2 hours)

### Sprint 4: JJM & Final Integration
- [ ] JJM community-based logic (3 hours)
- [ ] Geographic targeting (3 hours)
- [ ] Cross-scheme validation (2 hours)
- [ ] End-to-end testing (4 hours)

### Sprint 5: UI & Documentation
- [ ] Eligibility UI components (5 hours)
- [ ] Questionnaire forms (4 hours)
- [ ] Documentation updates (3 hours)

---

**Quick Reference Generated:** 2026-09-11  
**For:** Backend, Frontend, QA Implementation Teams  
**Status:** Ready for use in daily development  

