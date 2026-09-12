#!/usr/bin/env python3
"""
Extract eligibility criteria from government scheme PDFs.
Uses pymupdf to extract text and structure eligibility information.
"""

import fitz
import json
import os
from pathlib import Path
from typing import Dict, List, Any

# Define the schemes to process
SCHEMES = {
    "PM_Street_Vendor_AtmaNirbhar_Nidhi_PM_SVANidhi_3.pdf": {
        "scheme_id": "PM-SVANidhi",
        "scheme_name": "PM Street Vendor AtmaNirbhar Nidhi (PM-SVANidhi) - Street Vendors Scheme"
    },
    "PM_Vishwakarma_Yojana.pdf": {
        "scheme_id": "PM-Vishwakarma",
        "scheme_name": "PM Vishwakarma Yojana - Artisans Scheme"
    },
    "Pradhan_Mantri_Awas_Yojana_-_Urban_PMAY-U_2.pdf": {
        "scheme_id": "PMAY-U",
        "scheme_name": "Pradhan Mantri Awas Yojana - Urban (PMAY-U) - Urban Housing"
    },
    "Pradhan_Mantri_Matru_Vandana_Yojana_PMMVY.pdf": {
        "scheme_id": "PMMVY",
        "scheme_name": "Pradhan Mantri Matru Vandana Yojana (PMMVY) - Maternity Benefit"
    }
}

def extract_pdf_text(pdf_path: str) -> List[Dict[str, Any]]:
    """Extract text content from PDF with page numbers."""
    pages_content = []
    
    try:
        doc = fitz.open(pdf_path)
        for page_num, page in enumerate(doc, 1):
            text = page.get_text()
            pages_content.append({
                "page": page_num,
                "text": text
            })
        doc.close()
        return pages_content
    except Exception as e:
        return [{"page": 0, "error": str(e)}]

def extract_scheme_eligibility(pdf_path: str, scheme_info: Dict[str, str]) -> Dict[str, Any]:
    """Extract eligibility information from a scheme PDF."""
    
    result = {
        "scheme_id": scheme_info["scheme_id"],
        "scheme_name": scheme_info["scheme_name"],
        "pdf_filename": os.path.basename(pdf_path),
        "full_pdf_path": pdf_path,
        "extraction_status": "completed",
        "beneficiary_scope": "NOT SPECIFIED IN PDF",
        "eligibility_criteria": [],
        "exclusion_criteria": [],
        "required_documents": [],
        "age_restrictions": {
            "minimum": "NOT SPECIFIED IN PDF",
            "maximum": "NOT SPECIFIED IN PDF"
        },
        "gender_restrictions": "NOT SPECIFIED IN PDF",
        "income_limits": {
            "type": "NOT SPECIFIED IN PDF",
            "value": "NOT SPECIFIED IN PDF",
            "currency": "NOT SPECIFIED IN PDF"
        },
        "social_category_preferences": [],
        "geographic_restrictions": {
            "state_specific": "NOT SPECIFIED IN PDF",
            "rural_urban": "NOT SPECIFIED IN PDF",
            "details": []
        },
        "other_requirements": [],
        "raw_pages_content": []
    }
    
    try:
        # Extract pages
        pages = extract_pdf_text(pdf_path)
        
        # Process pages to extract sections
        full_text = "\n".join([p.get("text", "") for p in pages])
        result["raw_pages_content"] = pages
        
        # Search for key sections
        keywords = {
            "eligibility": [
                "eligibility", "eligible", "criteria", "requirements", "who is eligible",
                "qualification", "entitled", "can apply", "applicant eligibility"
            ],
            "exclusion": [
                "not eligible", "exclusion", "excluded", "shall not be",
                "disqualification", "ineligible", "who is not eligible"
            ],
            "documents": [
                "documents required", "required documents", "documentation", 
                "certificate", "proof", "submit", "furnish", "attach"
            ],
            "age": ["age", "years old", "minimum age", "maximum age", "age limit"],
            "gender": ["male", "female", "woman", "gender", "sex"],
            "income": [
                "income", "annual income", "income limit", "income ceiling",
                "family income", "income group", "income limit"
            ],
            "social": [
                "sc", "st", "obc", "scheduled caste", "scheduled tribe",
                "backward", "category", "general", "social category"
            ],
            "geographic": [
                "state", "rural", "urban", "district", "area", "region",
                "location", "residence", "domicile"
            ],
            "beneficiary": [
                "individual", "family", "enterprise", "institution",
                "beneficiary", "applicant", "eligible person", "targeting"
            ]
        }
        
        # Extract sections containing key information
        lines = full_text.split('\n')
        
        # Detailed extraction by searching for sections
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            # Check for beneficiary scope
            if any(kw in line_lower for kw in keywords["beneficiary"]):
                if "individual" in line_lower and result["beneficiary_scope"] == "NOT SPECIFIED IN PDF":
                    result["beneficiary_scope"] = "INDIVIDUAL"
                elif "family" in line_lower and "individual" not in result["beneficiary_scope"]:
                    result["beneficiary_scope"] = "FAMILY"
                elif "enterprise" in line_lower:
                    result["beneficiary_scope"] = "ENTERPRISE"
            
            # Check for eligibility criteria
            if any(kw in line_lower for kw in keywords["eligibility"]):
                if line.strip() and len(line.strip()) > 10:
                    # Try to find the page number
                    page_num = "unknown"
                    for page in pages:
                        if line.strip() in page.get("text", ""):
                            page_num = page["page"]
                            break
                    result["eligibility_criteria"].append({
                        "text": line.strip(),
                        "page": page_num,
                        "type": "REQUIRED"
                    })
            
            # Check for exclusion criteria
            if any(kw in line_lower for kw in keywords["exclusion"]):
                if line.strip() and len(line.strip()) > 10:
                    page_num = "unknown"
                    for page in pages:
                        if line.strip() in page.get("text", ""):
                            page_num = page["page"]
                            break
                    result["exclusion_criteria"].append({
                        "text": line.strip(),
                        "page": page_num,
                        "type": "EXCLUSION"
                    })
            
            # Check for age restrictions
            if "age" in line_lower and any(num in line for num in 
                ["18", "21", "30", "35", "40", "45", "50", "55", "60", "65", "70"]):
                if result["age_restrictions"]["minimum"] == "NOT SPECIFIED IN PDF":
                    result["age_restrictions"]["details"] = line.strip()
        
        # Clean up duplicates
        result["eligibility_criteria"] = result["eligibility_criteria"][:20]  # Limit output
        result["exclusion_criteria"] = result["exclusion_criteria"][:10]  # Limit output
        
    except Exception as e:
        result["extraction_status"] = f"error: {str(e)}"
    
    return result

def main():
    """Main extraction function."""
    data_dir = Path("data")
    
    all_schemes_data = {}
    
    print("Starting PDF eligibility extraction...\n")
    
    for pdf_filename, scheme_info in SCHEMES.items():
        pdf_path = data_dir / pdf_filename
        
        print(f"Processing: {scheme_info['scheme_name']}")
        print(f"  File: {pdf_filename}")
        
        if not pdf_path.exists():
            print(f"  ERROR: File not found: {pdf_path}\n")
            continue
        
        # Extract eligibility information
        scheme_data = extract_scheme_eligibility(str(pdf_path), scheme_info)
        all_schemes_data[scheme_info["scheme_id"]] = scheme_data
        
        print(f"  Status: {scheme_data['extraction_status']}")
        print(f"  Eligibility criteria found: {len(scheme_data['eligibility_criteria'])}")
        print(f"  Exclusion criteria found: {len(scheme_data['exclusion_criteria'])}\n")
    
    # Save results
    output_file = Path("eligibility_extraction_results.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_schemes_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nExtraction complete! Results saved to: {output_file}")
    
    # Print summary
    print("\n" + "="*70)
    print("EXTRACTION SUMMARY")
    print("="*70)
    
    for scheme_id, data in all_schemes_data.items():
        print(f"\n{scheme_id}: {data['scheme_name']}")
        print(f"  Eligibility Criteria: {len(data['eligibility_criteria'])}")
        print(f"  Exclusion Criteria: {len(data['exclusion_criteria'])}")
        print(f"  Pages Extracted: {len(data['raw_pages_content'])}")
    
    return all_schemes_data

if __name__ == "__main__":
    all_data = main()
