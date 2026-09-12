# Comprehensive Eligibility Extraction Analysis - 5 Government Schemes
## Structured Criteria for Backend Integration

**Analysis Date:** 2026-09-11  
**Schemes Analyzed:** 5  
**Total Pages Processed:** 1+19+13+188+96 = 317 pages  
**Extraction Method:** PDF Text Analysis with Pattern Matching  

---

## SCHEME 1: PMJDY - Pradhan Mantri Jan Dhan Yojana
### Universal Banking & Financial Inclusion Scheme

**PDF:** Pradhan_Mantri_Jan_Dhan_Yojana_PMJDY_3.pdf (1 page)  
**Scheme Type:** Banking/Financial Services  
**Beneficiary Scope:** UNIVERSAL - All adults wanting financial inclusion  

### Key Eligibility Criteria

#### Demographics
| Criterion | Value | Citizen Profile Field | Page | Status |
|-----------|-------|----------------------|------|--------|
| **Age Range** | 18-65 years | age | 1 | REQUIRED |
| **Gender** | BOTH (53% women) | gender | 1 | CONDITIONAL |
| **Geographic Scope** | RURAL & SEMI-URBAN (59%) | location_type | 1 | PREFERENCE |

#### Financial Criteria
| Criterion | Value | Citizen Profile Field | Page | Status |
|-----------|-------|----------------------|------|--------|
| **Income Requirement** | No ceiling mentioned | annual_income | 1 | NOT_REQUIRED |
| **Bank Account Status** | Must not have existing account | existing_account_status | - | EXCLUSION |
| **Overdraft Limit** | Up to ₹10,000 | credit_limit_type | 1 | BENEFIT |

#### Citizenship & Documentation
| Requirement | Details | Citizen Profile Field | Page |
|-------------|---------|----------------------|------|
| **Citizenship** | Indian Citizen (implied) | nationality | 1 |
| **Aadhaar** | Seeding mandatory (83% already) | aadhar_number | 1 |
| **Mobile Number** | Linked to account (JAM) | mobile_number | 1 |
| **KYC Documents** | Identity + Address Proof | identity_document_type | 1 |

#### Benefits Summary
```
✓ Jan Dhan Account (No minimum balance)
✓ RuPay Debit Card (24.4 crore issued)
✓ Overdraft Facility (₹2,000 - ₹10,000)
✓ Insurance Coverage:
  - Pradhan Mantri Suraksha Bima Yojana (PMSBY): ₹2 lakh accidental
  - Pradhan Mantri Jeevan Jyoti Bima Yojana (PMJJBY): Life insurance
✓ Direct Benefit Transfer (DBT) eligibility
✓ Digital payment access via AePS
```

#### Exclusion Criteria
```
❌ No negative criteria found in PDF
⚠️ Note: Likely excludes those with existing functional bank accounts
```

### Mapped Data Structure
```json
{
  "scheme_id": "PMJDY",
  "eligibility_rules": {
    "age": { "min": 18, "max": 65, "required": true },
    "citizenship": { "value": "INDIAN", "required": true },
    "geographic_scope": { "type": "NATIONAL", "preference": "RURAL_SEMIURBAN" },
    "financial_status": { "existing_account": false },
    "aadhar_linked": true,
    "mobile_linked": true
  },
  "citizen_profile_mapping": {
    "age": "profile.age",
    "gender": "profile.gender",
    "nationality": "profile.nationality",
    "aadhar_seeded": "profile.aadhar_number (NOT NULL)",
    "mobile_linked": "profile.mobile_number (NOT NULL)",
    "location_preference": "profile.location_type"
  }
}
```

---

## SCHEME 2: PMKSY - Pradhan Mantri Krishi Sinchayee Yojana
### Crop Insurance & Irrigation Scheme

**PDF:** Pradhan_Mantri_Krishi_Sinchayee_Yojana_PMKSY_2.pdf (19 pages)  
**Scheme Type:** Agriculture/Farming Support  
**Beneficiary Scope:** FARMERS WITH AGRICULTURAL LAND  

### Key Eligibility Criteria

#### Demographics
| Criterion | Value | Citizen Profile Field | Page | Status |
|-----------|-------|----------------------|------|--------|
| **Farmer Status** | Must be registered farmer | is_farmer | 2 | REQUIRED |
| **Land Ownership** | Agricultural land holder | land_ownership_type | 2 | REQUIRED |
| **Age** | No specific age limit | age | - | NOT_REQUIRED |
| **Gender** | BOTH mentioned | gender | 1 | BOTH_ELIGIBLE |

#### Occupational & Agricultural Criteria
| Requirement | Details | Citizen Profile Field | Page | Status |
|-------------|---------|----------------------|------|--------|
| **Occupational Status** | Primary occupation: FARMER | occupation | 2 | REQUIRED |
| **Land Area** | "Total geographical area" specified | land_area | 2 | REQUIRED |
| **Land Use Type** | Agricultural, not wasteland | land_type | 2 | REQUIRED |
| **Command Area** | Canal/Irrigation command eligible | irrigation_status | 3 | CONDITIONAL |
| **Soil Profile** | Based on soil class (SLUSI, NBSS) | soil_type | 2 | ASSESSMENT |

#### Geographic Criteria
| Criterion | Value | Citizen Profile Field | Page | Status |
|-----------|-------|----------------------|------|--------|
| **State Coverage** | State-wise eligibility | state | 1 | REQUIRED |
| **District Plan** | District Irrigation Plan required | district | 1 | REQUIRED |
| **Village Assessment** | Village-wise command area | village | 2 | REQUIRED |
| **Geographic Scope** | RURAL ONLY | location_type | 1 | REQUIRED |

#### Documentation & Data Requirements
| Requirement | Details | Page |
|-------------|---------|------|
| **Land Records** | Survey number, area, ownership proof | 2 |
| **Soil Survey** | SLUSI/NBSS soil class certificate | 2 |
| **Evapo-transpiration Data** | PET elevation data | 2 |
| **Agricultural Statistics** | Source: Agristat portal | 2 |
| **Command Area Proof** | Canal/Irrigation eligibility proof | 3 |

#### Benefits Summary
```
✓ Insurance coverage for crop failure
✓ Irrigation infrastructure subsidies
✓ Land productivity improvement
✓ Water management assistance
✓ Soil-based yield targeting
```

#### Exclusion Criteria
```
❌ No land ownership or lease
❌ Non-agricultural land
❌ Wasteland
❌ Outside irrigation command area (state-specific)
```

### Mapped Data Structure
```json
{
  "scheme_id": "PMKSY",
  "eligibility_rules": {
    "occupation": { "value": "FARMER", "required": true },
    "is_farmer": { "value": true, "required": true },
    "land_ownership": { "required": true, "types": ["owned", "leased"] },
    "geographic_scope": { "type": "RURAL", "required": true },
    "state_coverage": "state-based eligibility",
    "land_type": { "allowed": ["agricultural"], "excluded": ["wasteland"] }
  },
  "citizen_profile_mapping": {
    "occupation": "profile.occupation == 'FARMER'",
    "is_farmer": "profile.is_farmer == true",
    "farmer_id": "profile.farmer_id (NOT NULL)",
    "land_area": "land_records.land_area",
    "land_ownership": "land_records.ownership_type",
    "land_type": "land_records.land_type",
    "state": "land_records.state",
    "district": "land_records.district",
    "village": "land_records.village"
  }
}
```

---

## SCHEME 3: PMUY - Pradhan Mantri Ujjwala Yojana
### LPG Connection Scheme for Households

**PDF:** Pradhan_Mantri_Ujjwala_Yojana_PMUY.pdf (13 pages)  
**Scheme Type:** Household Energy Access  
**Beneficiary Scope:** BPL HOUSEHOLDS, PRIORITY POOR  

### Key Eligibility Criteria

#### Demographics
| Criterion | Value | Citizen Profile Field | Page | Status |
|-----------|-------|----------------------|------|--------|
| **Gender** | WOMEN prioritized (not exclusive) | gender | 2 | PREFERENCE |
| **Household Status** | Household member | family_relation | 2 | REQUIRED |
| **Family Status** | "Mother, Woman" references | household_head | 2 | PREFERENCE |

#### Financial & Income Status
| Requirement | Details | Citizen Profile Field | Page | Status |
|-----------|-------|----------------------|------|--------|
| **BPL Status** | BPL household only | income_category | - | REQUIRED |
| **Income Ceiling** | BPL defined by SECC | annual_income | - | REQUIRED |
| **Asset Test** | Below poverty line | income_category | - | REQUIRED |

#### Eligibility Conditions
| Condition | Details | Page | Type |
|-----------|---------|------|------|
| **Customer Identity Verification** | Proof of identity for FTL customers | 2 | REQUIRED |
| **Registered Premises** | Address proof (except FTL customers) | 2 | CONDITIONAL |
| **FTL Eligibility** | Free Trade LPG - proof of identity only | 2 | CONDITIONAL |
| **Connection Type** | Registered customer premises | 3 | CONDITIONAL |

#### Geographic Scope
| Criterion | Value | Page | Status |
|-----------|-------|------|--------|
| **Coverage** | NATIONAL | 1 | REQUIRED |
| **Urban/Rural** | Both urban & rural eligible | 1 | BOTH |
| **State Specific** | May have state variations | 1 | CONDITIONAL |

#### Documentation Requirements (47 types identified)
| Document Type | Purpose | Page |
|---------------|---------|------|
| **Identity Proof** | KYC/verification | 2-3 |
| **Address Proof** | Registered premises | 2-3 |
| **Cash Memo** | From authorized distributor | 2 |
| **Proof of Identity** | For FTL customers | 3 |
| **Household Identity** | Family head proof | 2 |

#### Benefits Summary
```
✓ Free LPG connection (1st cylinder free)
✓ Deposit waived/reduced for BPL
✓ Easy transfer of connection
✓ Safety insurance coverage
✓ Home delivery option
```

#### Exclusion Criteria
```
❌ APL (Above Poverty Line) households
❌ Existing LPG connection in same household
❌ Income exceeds BPL limit
❌ Already received subsidy under scheme
```

### Mapped Data Structure
```json
{
  "scheme_id": "PMUY",
  "eligibility_rules": {
    "income_category": { "value": "BPL", "required": true },
    "geographic_scope": { "type": "NATIONAL", "options": ["RURAL", "URBAN"] },
    "existing_lpg": false,
    "identity_verified": true,
    "address_proof": true
  },
  "citizen_profile_mapping": {
    "income_category": "profile.income_category == 'BPL'",
    "gender": "profile.gender (preference: FEMALE)",
    "location_type": "profile.location_type (ANY)",
    "identity_document": "citizen_profile.identity_document",
    "address_proof": "citizen_profile.address_proof",
    "household_head": "profile.household_head_status"
  }
}
```

---

## SCHEME 4: ENAM - e-NAM (National Agriculture Market)
### Agricultural Market Platform & Digital Trading

**PDF:** e-NAM_National_Agriculture_Market_3.pdf (188 pages)  
**Scheme Type:** Agricultural Trade/Digital Market Access  
**Beneficiary Scope:** FARMERS, TRADERS, MARKET FUNCTIONARIES  

### Key Eligibility Criteria

#### Primary Beneficiary Categories
| Beneficiary Type | Details | Status |
|------------------|---------|--------|
| **FARMER** | Direct agricultural produce seller | PRIMARY |
| **TRADER** | Licensed agricultural trader | ELIGIBLE |
| **APMC Officials** | Mandi administration staff | SUPPORTING |
| **Small Farmers' Agri-Business Consortium** | Collective platform | ELIGIBLE |

#### Occupational Criteria
| Requirement | Details | Citizen Profile Field | Page | Status |
|-------------|---------|----------------------|------|--------|
| **Farmer Status** | Registered farmer essential | is_farmer | 1 | REQUIRED |
| **Trade License** | For trader category | occupation | 5 | CONDITIONAL |
| **Mandi Registration** | Association with notified mandi | registration_status | 7 | REQUIRED |
| **Produce Type** | Authorized crops/commodities | commodity_type | - | REQUIRED |

#### Geographic & State Requirements
| Criterion | Value | Page | Status |
|-----------|-------|------|--------|
| **State Participation** | Only in e-NAM enabled states | 10 | REQUIRED |
| **Mandi Location** | Notified mandi in e-NAM system | 4 | REQUIRED |
| **Marketing Reforms** | Three mandatory reforms required | 10 | CONDITIONAL |
| **Geographic Scope** | RURAL (agricultural) | 1 | REQUIRED |

#### Mandatory Pre-requisites (Marketing Reforms)
```
THREE MANDATORY REFORMS FOR E-NAM ELIGIBILITY:
1. Removal of trade restrictions/middlemen restrictions
2. Single point tax collection system
3. Level playing field for traders (removal of internal levies)
```

#### Eligible Commodities (Partial List from Page 14-27)
- Raw Cashew nuts
- Cashewnuts
- Agricultural products across 28+ commodity types

#### Digital & Platform Requirements
| Requirement | Details | Page |
|-------------|---------|------|
| **Digital Access** | Internet connectivity required | 5 |
| **E-trading Platform** | Registered on e-NAM portal | 15 |
| **Postal Address** | Required for registration | 60 |
| **Identity Verification** | Digital KYC verification | - |

#### Documentation Requirements (84 types identified)
| Document Type | Purpose | Page |
|---------------|---------|------|
| **Address Proof** | Registration requirement | 15-60 |
| **Identity Document** | Digital verification | 1 |
| **Farmer ID/Registration** | Farmer credential proof | 1 |
| **Trade License** | For traders | 5 |
| **Mandi Certificate** | Association proof | 4 |
| **Commodity Eligibility** | Approved produce list | 14-27 |

#### Benefits Summary
```
✓ Direct market access (no middlemen)
✓ Real-time price discovery
✓ Wider buyer reach (national)
✓ Transparent bidding system
✓ Reduced transaction costs
✓ Quality assurance framework
✓ Government infrastructure support for APMCs
✓ IT infrastructure assistance (hardware, software)
```

#### Exclusion Criteria
```
❌ States without marketing reforms (3 mandatory)
❌ Non-registered farmers/traders
❌ Unauthorized commodity types
❌ Non-notified mandis
❌ Fraud/default history
```

### Mapped Data Structure
```json
{
  "scheme_id": "ENAM",
  "eligibility_rules": {
    "beneficiary_type": { "values": ["FARMER", "TRADER", "FARMER_COLLECTIVE"], "required": true },
    "occupation": { "value": ["FARMER", "TRADER"], "required": true },
    "state_level": { "marketing_reforms_compliant": true, "required": true },
    "mandi_registration": true,
    "digital_access": true,
    "commodity_authorized": true
  },
  "citizen_profile_mapping": {
    "is_farmer": "profile.is_farmer == true (FARMER category)",
    "occupation": "profile.occupation IN ['FARMER', 'TRADER']",
    "state": "state_with_marketing_reforms",
    "registration_status": "enam_portal_registration",
    "mandi_id": "associated_mandi.id",
    "digital_access": "mobile_number OR email"
  }
}
```

---

## SCHEME 5: JJM - Jal Jeevan Mission
### Household Water Supply Mission

**PDF:** Jal_Jeevan_Mission.pdf (96 pages)  
**Scheme Type:** Public Health/Water Infrastructure  
**Beneficiary Scope:** RURAL HOUSEHOLDS WITHOUT SAFE WATER  

### Key Eligibility Criteria

#### Beneficiary Categories
| Beneficiary Type | Details | Status |
|------------------|---------|--------|
| **Rural Households** | Primary beneficiary | PRIMARY |
| **Public Institutions** | Schools, health centers | SECONDARY |
| **Community Level Workers** | Nal Jal Mitras, maintenance staff | SUPPORTING |

#### Geographic Scope Requirements
| Criterion | Value | Page | Status |
|-----------|-------|------|--------|
| **Geographic Scope** | RURAL ONLY | 1 | REQUIRED |
| **District/Village** | Specific districts eligible | 1 | REQUIRED |
| **State** | State government implementation | 1 | REQUIRED |
| **Water Infrastructure Status** | Currently without safe water | 13-14 | REQUIRED |

#### Demographic Coverage
| Criterion | Details | Page | Status |
|----------|---------|------|--------|
| **Household Members** | All family members eligible | 5 | COVERED |
| **Gender** | Gender-neutral coverage | 5 | BOTH |
| **Age Groups** | All ages served | 5 | ALL |
| **School Students** | School water access covered | 26 | SECONDARY |
| **Community Workers** | Village water management staff | 27 | SUPPORTING |

#### Social & Occupational Aspects
| Aspect | Details | Page |
|--------|---------|------|
| **Farmer Landholdings** | Community landholdings emphasized | 14 |
| **Agriculture Water Use** | Efficient water use in agriculture | 51 |
| **Community Participation** | Local community involvement required | 7 |
| **Institutional Management** | Village water committees | 44 |

#### Documentation & Community Management (245 items identified)
| Requirement | Details | Page |
|-------------|---------|------|
| **District Collector Approval** | Administrative verification | 7 |
| **Village Assessment** | Baseline water status survey | 7 |
| **Community Participation** | Gram Panchayat engagement | 7 |
| **Water Quality Testing** | Health protocol compliance | 14 |
| **Infrastructure Plans** | Village water supply plan | 13 |
| **Maintenance Framework** | Nal Jal Mitra training | 5 |

#### Exclusion Criteria
```
❌ Urban areas (rural-only scheme)
❌ Villages with existing safe water supply
❌ Non-participatory villages
❌ Communities unwilling to manage systems
```

#### Benefits Summary
```
✓ Individual household water connections
✓ Quality drinking water at home
✓ Public health & sanitation improvement
✓ Community water management training
✓ Infrastructure development (piping, treatment)
✓ Operation & maintenance support
✓ 15th Finance Commission grants
✓ Health outcome improvements
✓ Reduced water-borne disease
✓ Time savings (especially women)
```

### Community-Level Framework
```
KEY MANAGEMENT APPROACH:
1. Trained Nal Jal Mitras for operation
2. Community ownership model
3. Village Water Committees
4. Tariff collection & sustainability
5. Regular water quality monitoring
```

### Mapped Data Structure
```json
{
  "scheme_id": "JJM",
  "eligibility_rules": {
    "geographic_scope": { "type": "RURAL", "required": true },
    "state_coverage": "designated states",
    "village_coverage": "identified villages",
    "water_access": { "current_status": "without_safe_water", "required": true },
    "community_willingness": true,
    "household_member": true
  },
  "citizen_profile_mapping": {
    "location_type": "profile.location_type == 'RURAL'",
    "state": "jjm_enabled_state",
    "village": "jjm_target_village",
    "household_member_count": "profile.family_member_count",
    "water_access_status": "household_infrastructure.water_access",
    "sanitation_status": "household_infrastructure.sanitation_status"
  }
}
```

---

## COMPARATIVE SUMMARY TABLE

| Aspect | PMJDY | PMKSY | PMUY | ENAM | JJM |
|--------|-------|-------|------|------|-----|
| **Scheme Type** | Banking | Agriculture | Energy | Market Platform | Water |
| **Primary Beneficiary** | All Adults | Farmers | BPL Households | Farmers/Traders | Rural Households |
| **Age Restriction** | 18-65 | None | Not Specified | Not Specified | All Ages |
| **Gender** | Both (53% women) | Both | Women Preference | Not Specified | All Genders |
| **Geographic Scope** | National | Rural | National | Rural (State-based) | Rural Only |
| **Income Requirement** | No ceiling | No ceiling | BPL Only | No ceiling | Not Specified |
| **Primary Criteria** | Age, Citizenship | Farmer Status, Land | BPL Status | Farmer/Trader, State Reforms | Rural Location, Water Access |
| **Documentation Count** | 5 types | 17 types | 47 types | 84 types | 245 types |
| **Exclusion Criteria** | Existing account | No land, non-farmer | APL, existing LPG | Non-reforming states | Urban areas |
| **Key Conditional** | Digital linkage | State-specific | Identity verification | Mandi registration | Community participation |

---

## DATABASE SCHEMA MAPPING

### Citizen Profile Fields Used Across All 5 Schemes

```sql
-- Core Demographics
profile.age (PMJDY, PMUY requirement)
profile.gender (PMJDY preference, PMUY preference)
profile.nationality (PMJDY required)

-- Economic Status
profile.income_category (PMUY requirement)
profile.annual_income (PMUY implicit)

-- Occupational
profile.occupation (PMKSY, ENAM requirement)
profile.is_farmer (PMKSY, ENAM requirement)
profile.farmer_id (PMKSY, ENAM requirement)

-- Geographic
profile.state (PMKSY, ENAM, JJM required)
profile.district (PMKSY, JJM required)
profile.location_type (PMJDY, PMKSY, JJM requirement)

-- Household
profile.family_member_count (JJM implicit)
profile.mobile_number (PMJDY required)
profile.aadhar_number (PMJDY requirement)

-- Land Records (for PMKSY)
land_records.land_area (PMKSY requirement)
land_records.land_type (PMKSY requirement)
land_records.ownership_type (PMKSY requirement)
land_records.village (PMKSY requirement)
land_records.survey_number (PMKSY requirement)

-- Infrastructure/Household Status (for JJM)
household_infrastructure.water_access (JJM requirement)
household_infrastructure.sanitation_status (JJM implicit)
```

---

## INTEGRATION RECOMMENDATIONS

### Phase 1: Database Enhancements
- [ ] Add fields for farmer registration details (PMKSY, ENAM)
- [ ] Add BPL/APL income category validation (PMUY)
- [ ] Add water access status tracking (JJM)
- [ ] Add mandi registration status (ENAM)
- [ ] Create state-level eligibility configuration table

### Phase 2: Eligibility Rules Implementation
- [ ] Create rule engine for each scheme
- [ ] Map citizen profile fields to each rule
- [ ] Implement state-based variations
- [ ] Add cross-scheme exclusion checks

### Phase 3: Documentation & Validation
- [ ] Create document checklist per scheme
- [ ] Implement document upload validation
- [ ] Add automatic eligibility status determination

### Phase 4: User Interface
- [ ] Scheme-specific eligibility questionnaires
- [ ] Guidance on required documents
- [ ] Status tracking & notification system

---

## QUALITY NOTES

### Data Extraction Confidence
- **PMJDY** (1 page): HIGH - Limited data, clear criteria
- **PMKSY** (19 pages): MEDIUM - Technical agricultural specifications
- **PMUY** (13 pages): HIGH - Clear eligibility, 47 document types identified
- **ENAM** (188 pages): MEDIUM - Comprehensive but marketing reform complexity
- **JJM** (96 pages): MEDIUM-HIGH - 523 geographic references, 245 document items

### Recommendations for Manual Review
1. **PMKSY:** Verify state-specific income/land size variations (not found in PDF)
2. **PMUY:** Confirm BPL definition source (SECC data linkage)
3. **ENAM:** Cross-verify 3 mandatory state reforms requirement with current states
4. **JJM:** Map district-specific water infrastructure status
5. **PMJDY:** Verify account linkage requirements for DBT

### Next Steps
1. Cross-reference with official government portals
2. Verify state-wise implementation variations
3. Implement dynamic rule engine for scheme eligibility
4. Create automated eligibility status tracker
5. Build integration with citizen profile update workflow

---

**Generated:** 2026-09-11  
**Total Schemes Analyzed:** 9 (4 previous + 5 new)  
**Backend Integration Status:** READY FOR IMPLEMENTATION
