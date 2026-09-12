#!/usr/bin/env python3
"""
Extract eligibility criteria from 5 government scheme PDFs:
1. Pradhan Mantri Jan Dhan Yojana (PM-JDY)
2. Pradhan Mantri Krishi Sinchayee Yojana (PMKSY)
3. Pradhan Mantri Ujjwala Yojana (PM-UJY)
4. e-NAM (National Agriculture Market)
5. Jal Jeevan Mission (JJM)
"""

import fitz
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

@dataclass
class EligibilityCriterion:
    """Represents a single eligibility criterion."""
    criterion_type: str  # REQUIRED, EXCLUSION, CONDITIONAL, PREFERENCE
    category: str  # DEMOGRAPHIC, FINANCIAL, OCCUPATIONAL, GEOGRAPHIC, EDUCATIONAL, HEALTH
    description: str
    values: List[str]  # Specific values/ranges
    page_reference: int
    exact_quote: str
    citizen_profile_field: str  # Field from citizen profile schema

class SchemeEligibilityExtractor:
    """Extract eligibility criteria from government scheme PDFs."""
    
    def __init__(self, pdf_path: str, scheme_info: Dict[str, str]):
        self.pdf_path = pdf_path
        self.scheme_info = scheme_info
        self.doc = None
        self.pages_text = []
        self.full_text = ""
        self._load_pdf()
    
    def _load_pdf(self):
        """Load PDF and extract text by page."""
        try:
            self.doc = fitz.open(self.pdf_path)
            for page_num in range(len(self.doc)):
                page = self.doc[page_num]
                text = page.get_text()
                self.pages_text.append({
                    "page_number": page_num + 1,
                    "text": text
                })
            self.full_text = "\n".join([p["text"] for p in self.pages_text])
        except Exception as e:
            print(f"Error loading PDF {self.pdf_path}: {e}")
    
    def _find_page_for_text(self, text_snippet: str) -> int:
        """Find which page contains a text snippet."""
        for page_data in self.pages_text:
            if text_snippet in page_data["text"]:
                return page_data["page_number"]
        return 1  # Default to first page
    
    def _extract_section(self, pattern: str, context_lines: int = 3) -> List[Dict]:
        """Extract all matches for a pattern with context."""
        matches = []
        lines = self.full_text.split('\n')
        
        for i, line in enumerate(lines):
            if re.search(pattern, line, re.IGNORECASE) and len(line.strip()) > 5:
                context_start = max(0, i - context_lines)
                context_end = min(len(lines), i + context_lines + 1)
                context = '\n'.join(lines[context_start:context_end]).strip()
                
                # Find page reference
                page_num = self._find_page_for_text(line)
                
                matches.append({
                    "snippet": line.strip(),
                    "context": context,
                    "page": page_num
                })
        
        return matches
    
    def extract_eligibility_criteria(self) -> Dict[str, Any]:
        """Extract all eligibility criteria from the PDF."""
        
        criteria = {
            "scheme_id": self.scheme_info["scheme_id"],
            "scheme_name": self.scheme_info["scheme_name"],
            "pdf_file": Path(self.pdf_path).name,
            "total_pages": len(self.pages_text),
            "extraction_metadata": {
                "extraction_date": "2026-09-11",
                "extraction_method": "PDF text extraction with pattern matching"
            },
            "demographics": {
                "age": self._extract_age_criteria(),
                "gender": self._extract_gender_criteria(),
                "marital_status": self._extract_marital_criteria(),
                "citizenship": self._extract_citizenship_criteria(),
            },
            "financial": {
                "income_limits": self._extract_income_criteria(),
                "asset_criteria": self._extract_asset_criteria(),
            },
            "social": {
                "caste_categories": self._extract_caste_criteria(),
                "community_specific": self._extract_community_criteria(),
            },
            "occupational": {
                "profession_eligibility": self._extract_occupation_criteria(),
                "farmer_status": self._extract_farmer_criteria(),
            },
            "geographic": {
                "scope": self._extract_geographic_scope(),
                "state_specific": self._extract_state_specific(),
            },
            "educational": {
                "education_requirements": self._extract_education_criteria(),
            },
            "health": {
                "disability_criteria": self._extract_disability_criteria(),
                "health_conditions": self._extract_health_criteria(),
            },
            "exclusion_criteria": self._extract_exclusion_criteria(),
            "required_documents": self._extract_documents_criteria(),
            "benefits_summary": self._extract_benefits_summary(),
            "special_conditions": self._extract_special_conditions(),
        }
        
        return criteria
    
    def _extract_age_criteria(self) -> List[Dict]:
        """Extract age-related eligibility criteria."""
        patterns = [
            r"age.*?(?:\d+)\s*(?:years?|yr?s?)(?:\s*-\s*)?(?:to\s*)?(?:\d+)?",
            r"(?:minimum|max)\s*age.*?\d+",
            r"\d+\s*years?\s*(?:and\s*above|old|minimum)",
            r"between\s+\d+\s*-\s*\d+\s*years?",
        ]
        
        results = []
        for pattern in patterns:
            matches = self._extract_section(pattern)
            results.extend(matches)
        
        # Deduplicate
        unique = {m["snippet"]: m for m in results}
        return list(unique.values())
    
    def _extract_gender_criteria(self) -> List[Dict]:
        """Extract gender-related criteria."""
        patterns = [
            r"(?:male|female|woman|women|mother|pregnant|widow|man|boy|girl)",
            r"gender.*?(?:male|female)",
        ]
        
        results = []
        for pattern in patterns:
            matches = self._extract_section(pattern)
            results.extend(matches)
        
        unique = {m["snippet"]: m for m in results}
        return list(unique.values())
    
    def _extract_marital_criteria(self) -> List[Dict]:
        """Extract marital status criteria."""
        patterns = [
            r"(?:married|unmarried|widow|widower|divorced|separated|single)",
            r"marital\s*status",
        ]
        
        results = []
        for pattern in patterns:
            matches = self._extract_section(pattern)
            results.extend(matches)
        
        unique = {m["snippet"]: m for m in results}
        return list(unique.values())
    
    def _extract_citizenship_criteria(self) -> List[Dict]:
        """Extract citizenship criteria."""
        patterns = [
            r"(?:citizen|citizenship|indian\s*citizen|nationality)",
            r"shall\s*be\s*(?:a\s*)?(?:indian\s*)?citizen",
        ]
        
        results = []
        for pattern in patterns:
            matches = self._extract_section(pattern)
            results.extend(matches)
        
        unique = {m["snippet"]: m for m in results}
        return list(unique.values())
    
    def _extract_income_criteria(self) -> List[Dict]:
        """Extract income limit criteria."""
        patterns = [
            r"income.*?(?:₹|\$|rs\.?|rupees?)\s*(?:\d+(?:,\d+)*)?",
            r"annual\s*income.*?\d+",
            r"family\s*income.*?\d+",
            r"income\s*limit\s*(?:not\s*)?exceed",
            r"(?:₹|\$|rs\.?)\s*(?:\d+(?:,\d+)*)\s*(?:per annum|annually|per year)",
        ]
        
        results = []
        for pattern in patterns:
            matches = self._extract_section(pattern)
            results.extend(matches)
        
        unique = {m["snippet"]: m for m in results}
        return list(unique.values())
    
    def _extract_asset_criteria(self) -> List[Dict]:
        """Extract asset-related criteria."""
        patterns = [
            r"asset.*?limit",
            r"property|land|house|vehicle",
            r"total\s*(?:value|worth).*?(?:₹|\$|rs\.?)",
        ]
        
        results = []
        for pattern in patterns:
            matches = self._extract_section(pattern)
            results.extend(matches)
        
        unique = {m["snippet"]: m for m in results}
        return list(unique.values())
    
    def _extract_caste_criteria(self) -> List[Dict]:
        """Extract caste/category criteria."""
        patterns = [
            r"(?:sc|st|obc|ews|general)",
            r"(?:scheduled\s*caste|scheduled\s*tribe|other\s*backward|caste|category)",
            r"social\s*category",
        ]
        
        results = []
        for pattern in patterns:
            matches = self._extract_section(pattern)
            results.extend(matches)
        
        unique = {m["snippet"]: m for m in results}
        return list(unique.values())
    
    def _extract_community_criteria(self) -> List[Dict]:
        """Extract community-specific criteria."""
        patterns = [
            r"(?:minority|tribal|indigenous|dalit)",
            r"religious\s*(?:community|group)",
        ]
        
        results = []
        for pattern in patterns:
            matches = self._extract_section(pattern)
            results.extend(matches)
        
        unique = {m["snippet"]: m for m in results}
        return list(unique.values())
    
    def _extract_occupation_criteria(self) -> List[Dict]:
        """Extract occupational criteria."""
        patterns = [
            r"occupation|profession|trade|business|employment|artisan|worker",
            r"self.?employed|unorganized\s*sector",
        ]
        
        results = []
        for pattern in patterns:
            matches = self._extract_section(pattern)
            results.extend(matches)
        
        unique = {m["snippet"]: m for m in results}
        return list(unique.values())
    
    def _extract_farmer_criteria(self) -> List[Dict]:
        """Extract farmer-specific criteria."""
        patterns = [
            r"farmer|farming|agriculture|cultivator|land\s*holding",
            r"agricultural\s*land",
        ]
        
        results = []
        for pattern in patterns:
            matches = self._extract_section(pattern)
            results.extend(matches)
        
        unique = {m["snippet"]: m for m in results}
        return list(unique.values())
    
    def _extract_geographic_scope(self) -> List[Dict]:
        """Extract geographic scope."""
        patterns = [
            r"(?:rural|urban|both|national|state|district)",
            r"scope.*?(?:rural|urban|state)",
            r"applicable.*?(?:area|region|state)",
        ]
        
        results = []
        for pattern in patterns:
            matches = self._extract_section(pattern)
            results.extend(matches)
        
        unique = {m["snippet"]: m for m in results}
        return list(unique.values())
    
    def _extract_state_specific(self) -> List[Dict]:
        """Extract state-specific variations."""
        patterns = [
            r"state.*?(?:shall|will|may|government)",
            r"(?:different|varies?|varies by)\s*(?:state|region)",
        ]
        
        results = []
        for pattern in patterns:
            matches = self._extract_section(pattern)
            results.extend(matches)
        
        unique = {m["snippet"]: m for m in results}
        return list(unique.values())
    
    def _extract_education_criteria(self) -> List[Dict]:
        """Extract education requirements."""
        patterns = [
            r"(?:education|educational|qualified|skill|training|literate|pass)",
            r"(?:primary|secondary|higher|graduate|diploma|certificate)",
        ]
        
        results = []
        for pattern in patterns:
            matches = self._extract_section(pattern)
            results.extend(matches)
        
        unique = {m["snippet"]: m for m in results}
        return list(unique.values())
    
    def _extract_disability_criteria(self) -> List[Dict]:
        """Extract disability-related criteria."""
        patterns = [
            r"(?:disabled|disability|disability%|persons?\s*with\s*disability|pwd)",
            r"handicap",
        ]
        
        results = []
        for pattern in patterns:
            matches = self._extract_section(pattern)
            results.extend(matches)
        
        unique = {m["snippet"]: m for m in results}
        return list(unique.values())
    
    def _extract_health_criteria(self) -> List[Dict]:
        """Extract health-related criteria."""
        patterns = [
            r"health|disease|medical|pregnant|lactating",
        ]
        
        results = []
        for pattern in patterns:
            matches = self._extract_section(pattern)
            results.extend(matches)
        
        unique = {m["snippet"]: m for m in results}
        return list(unique.values())
    
    def _extract_exclusion_criteria(self) -> List[Dict]:
        """Extract exclusion/disqualification criteria."""
        patterns = [
            r"(?:not\s*)?eligible|excluded|ineligible",
            r"shall\s*not\s*be\s*eligible",
            r"disqualification|excluded?",
            r"not\s*covered|not\s*apply",
        ]
        
        results = []
        for pattern in patterns:
            matches = self._extract_section(pattern, context_lines=2)
            results.extend(matches)
        
        unique = {m["snippet"]: m for m in results}
        return list(unique.values())
    
    def _extract_documents_criteria(self) -> List[Dict]:
        """Extract required documents."""
        patterns = [
            r"document|certificate|proof|identity|address",
            r"(?:submit|furnish|attach|provide|required)\s*(?:document|certificate|proof)",
            r"adhar|pan|voter|ration|bank|land",
        ]
        
        results = []
        for pattern in patterns:
            matches = self._extract_section(pattern)
            results.extend(matches)
        
        unique = {m["snippet"]: m for m in results}
        return list(unique.values())
    
    def _extract_benefits_summary(self) -> List[Dict]:
        """Extract benefit information."""
        patterns = [
            r"benefit|grant|subsidy|cash|financial|assistance|support",
            r"₹|rupees?|rs\.",
        ]
        
        results = []
        for pattern in patterns:
            matches = self._extract_section(pattern)
            results.extend(matches)
        
        # Keep only unique benefit-related lines
        unique = {m["snippet"]: m for m in results}
        filtered = [v for v in unique.values() if any(
            word in v["snippet"].lower() for word in ["benefit", "grant", "subsidy", "cash", "assistance", "₹", "rs"]
        )]
        return filtered[:10]  # Limit to top 10 benefit statements
    
    def _extract_special_conditions(self) -> List[Dict]:
        """Extract special conditions or restrictions."""
        patterns = [
            r"provided\s*that|subject\s*to|only\s*if|except",
            r"condition|restriction|constraint|limitation",
        ]
        
        results = []
        for pattern in patterns:
            matches = self._extract_section(pattern, context_lines=2)
            results.extend(matches)
        
        unique = {m["snippet"]: m for m in results}
        return list(unique.values())


def main():
    """Main extraction function."""
    
    # Define the 5 schemes
    schemes = [
        {
            "scheme_id": "PMJDY",
            "scheme_name": "Pradhan Mantri Jan Dhan Yojana",
            "file": "data/Pradhan_Mantri_Jan_Dhan_Yojana_PMJDY_3.pdf",
            "description": "Universal Banking Scheme"
        },
        {
            "scheme_id": "PMKSY",
            "scheme_name": "Pradhan Mantri Krishi Sinchayee Yojana",
            "file": "data/Pradhan_Mantri_Krishi_Sinchayee_Yojana_PMKSY_2.pdf",
            "description": "Crop Insurance/Irrigation Scheme"
        },
        {
            "scheme_id": "PMUY",
            "scheme_name": "Pradhan Mantri Ujjwala Yojana",
            "file": "data/Pradhan_Mantri_Ujjwala_Yojana_PMUY.pdf",
            "description": "LPG Connection Scheme"
        },
        {
            "scheme_id": "ENAM",
            "scheme_name": "e-NAM (National Agriculture Market)",
            "file": "data/e-NAM_National_Agriculture_Market_3.pdf",
            "description": "Agricultural Market Platform"
        },
        {
            "scheme_id": "JJM",
            "scheme_name": "Jal Jeevan Mission",
            "file": "data/Jal_Jeevan_Mission.pdf",
            "description": "Water Supply Mission"
        }
    ]
    
    # Extract eligibility criteria for all schemes
    all_results = {}
    
    for scheme in schemes:
        print(f"\n{'='*60}")
        print(f"Extracting: {scheme['scheme_name']} ({scheme['scheme_id']})")
        print(f"{'='*60}")
        
        pdf_path = scheme["file"]
        
        try:
            extractor = SchemeEligibilityExtractor(pdf_path, scheme)
            criteria = extractor.extract_eligibility_criteria()
            all_results[scheme["scheme_id"]] = criteria
            
            print(f"✓ Successfully extracted eligibility criteria")
            print(f"  - Total pages: {criteria['total_pages']}")
            print(f"  - Demographics found: {len(criteria['demographics']['age']) + len(criteria['demographics']['gender'])}")
            print(f"  - Financial criteria found: {len(criteria['financial']['income_limits'])}")
            print(f"  - Occupational criteria found: {len(criteria['occupational']['profession_eligibility'])}")
            print(f"  - Exclusion criteria found: {len(criteria['exclusion_criteria'])}")
            print(f"  - Documents required: {len(criteria['required_documents'])}")
            
        except FileNotFoundError:
            print(f"✗ PDF not found: {pdf_path}")
        except Exception as e:
            print(f"✗ Error extracting {scheme['scheme_id']}: {e}")
    
    # Save results to JSON
    output_file = "ELIGIBILITY_EXTRACTION_5_SCHEMES.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\n\n✓ Results saved to {output_file}")
    
    # Create comprehensive markdown report
    create_markdown_report(all_results)


def create_markdown_report(all_results: Dict[str, Any]):
    """Create a comprehensive markdown report."""
    
    report = """# Government Scheme Eligibility Extraction Report
## 5 Additional Schemes Analysis

**Extraction Date:** 2026-09-11  
**Schemes Analyzed:** 5  
**Analysis Method:** PDF Text Extraction with Pattern Matching

---

"""
    
    for scheme_id, criteria in all_results.items():
        scheme_name = criteria["scheme_name"]
        report += f"\n## {scheme_id}: {scheme_name}\n\n"
        report += f"**PDF File:** {criteria['pdf_file']}  \n"
        report += f"**Total Pages:** {criteria['total_pages']}  \n\n"
        
        # Demographics
        report += "### Demographics\n"
        if criteria['demographics']['age']:
            report += f"**Age Criteria:** {len(criteria['demographics']['age'])} criteria found\n"
            for item in criteria['demographics']['age'][:3]:
                report += f"- *Page {item['page']}:* {item['snippet']}\n"
        
        if criteria['demographics']['gender']:
            report += f"\n**Gender Criteria:** {len(criteria['demographics']['gender'])} criteria found\n"
            for item in criteria['demographics']['gender'][:3]:
                report += f"- *Page {item['page']}:* {item['snippet']}\n"
        
        # Financial
        report += "\n### Financial Criteria\n"
        if criteria['financial']['income_limits']:
            report += f"**Income Limits:** {len(criteria['financial']['income_limits'])} criteria found\n"
            for item in criteria['financial']['income_limits'][:3]:
                report += f"- *Page {item['page']}:* {item['snippet']}\n"
        
        # Occupational
        report += "\n### Occupational Eligibility\n"
        if criteria['occupational']['profession_eligibility']:
            report += f"**Profession/Trade Criteria:** {len(criteria['occupational']['profession_eligibility'])} criteria found\n"
            for item in criteria['occupational']['profession_eligibility'][:3]:
                report += f"- *Page {item['page']}:* {item['snippet']}\n"
        
        if criteria['occupational']['farmer_status']:
            report += f"\n**Farmer Criteria:** {len(criteria['occupational']['farmer_status'])} criteria found\n"
            for item in criteria['occupational']['farmer_status'][:3]:
                report += f"- *Page {item['page']}:* {item['snippet']}\n"
        
        # Geographic
        report += "\n### Geographic Scope\n"
        if criteria['geographic']['scope']:
            report += f"**Scope:** {len(criteria['geographic']['scope'])} references found\n"
            for item in criteria['geographic']['scope'][:3]:
                report += f"- *Page {item['page']}:* {item['snippet']}\n"
        
        # Exclusion
        report += "\n### Exclusion Criteria\n"
        if criteria['exclusion_criteria']:
            report += f"**Total:** {len(criteria['exclusion_criteria'])} criteria found\n"
            for item in criteria['exclusion_criteria'][:5]:
                report += f"- *Page {item['page']}:* {item['snippet']}\n"
        else:
            report += "No specific exclusion criteria found in PDF.\n"
        
        # Documents
        report += "\n### Required Documents\n"
        if criteria['required_documents']:
            report += f"**Total:** {len(criteria['required_documents'])} document requirements found\n"
            for item in criteria['required_documents'][:5]:
                report += f"- *Page {item['page']}:* {item['snippet']}\n"
        
        # Benefits
        report += "\n### Benefits Summary\n"
        if criteria['benefits_summary']:
            report += f"**Total:** {len(criteria['benefits_summary'])} benefit statements found\n"
            for item in criteria['benefits_summary'][:5]:
                report += f"- *Page {item['page']}:* {item['snippet']}\n"
        
        report += "\n---\n"
    
    # Save markdown report
    report_file = "ELIGIBILITY_EXTRACTION_5_SCHEMES.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✓ Markdown report saved to {report_file}")


if __name__ == "__main__":
    main()
