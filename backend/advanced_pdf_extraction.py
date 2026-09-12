#!/usr/bin/env python3
"""
Advanced PDF extraction for government scheme eligibility criteria.
Specifically extracts eligibility sections with context preservation.
"""

import fitz
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple

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

def extract_pdf_content_with_context(pdf_path: str, max_pages: int = None) -> Dict[str, Any]:
    """Extract full PDF content organized by page."""
    content = {
        "total_pages": 0,
        "pages": [],
        "full_text": ""
    }
    
    try:
        doc = fitz.open(pdf_path)
        content["total_pages"] = len(doc)
        
        pages_to_process = len(doc) if max_pages is None else min(max_pages, len(doc))
        
        for page_num in range(pages_to_process):
            page = doc[page_num]
            text = page.get_text()
            
            content["pages"].append({
                "page_number": page_num + 1,
                "text": text
            })
            content["full_text"] += f"\n--- PAGE {page_num + 1} ---\n{text}\n"
        
        doc.close()
    except Exception as e:
        content["error"] = str(e)
    
    return content

def find_eligibility_sections(text: str) -> List[Dict[str, Any]]:
    """Find sections containing eligibility information."""
    sections = []
    
    # Keywords that indicate eligibility-related sections
    section_headers = [
        r"(?i)(eligibility|eligible|criteria|who can apply|who is eligible|qualifications?|requirements?|who can be a|applicant profile)",
        r"(?i)(inclusion criteria|target beneficiar|eligible person|eligible individual|eligibility conditions?)",
        r"(?i)(entry criteria|skill requirements|education requirements|age group|income limit)"
    ]
    
    # Split text into lines
    lines = text.split('\n')
    
    # Find section headers and extract context around them
    for i, line in enumerate(lines):
        for pattern in section_headers:
            if re.search(pattern, line):
                # Found a potential header, extract surrounding lines
                start = max(0, i - 1)
                end = min(len(lines), i + 30)
                
                section_text = '\n'.join(lines[start:end])
                if len(section_text.strip()) > 20:
                    sections.append({
                        "header_line_number": i + 1,
                        "header": line.strip(),
                        "content": section_text.strip(),
                        "lines_count": end - start
                    })
                break
    
    return sections

def extract_specific_criteria(full_text: str, pages: List[Dict]) -> Dict[str, Any]:
    """Extract specific eligibility criteria."""
    
    criteria = {
        "beneficiary_scope": None,
        "age_minimum": None,
        "age_maximum": None,
        "gender": None,
        "income_limit": None,
        "income_type": None,
        "education_required": None,
        "rural_urban": None,
        "state_specific": None,
        "caste_category": None,
        "marital_status": None,
        "citizenship": None,
        "eligibility_paragraphs": [],
        "exclusion_paragraphs": [],
        "other_requirements": []
    }
    
    # Find eligibility sections
    eligibility_sections = find_eligibility_sections(full_text)
    
    # Extract from found sections
    for section in eligibility_sections:
        content = section["content"]
        criteria["eligibility_paragraphs"].append({
            "section_header": section["header"],
            "page_line": section["header_line_number"],
            "content": content[:500]  # First 500 chars
        })
    
    # Extract specific values using regex
    
    # Age extraction
    age_patterns = [
        r"(?:minimum age|age of|aged|age between|age (?:must be|should be|is))\s+(\d+)",
        r"(\d+)\s*(?:years|years old)",
    ]
    for pattern in age_patterns:
        matches = re.findall(pattern, full_text, re.IGNORECASE)
        if matches:
            if criteria["age_minimum"] is None:
                criteria["age_minimum"] = matches[0]
            break
    
    # Gender
    if re.search(r"(?i)(female|woman|women|mother|pregnant)", full_text):
        if not criteria["gender"]:
            criteria["gender"] = "Female"
    elif re.search(r"(?i)(male|man|men)", full_text):
        if not criteria["gender"]:
            criteria["gender"] = "Male"
    
    # Rural/Urban
    if re.search(r"(?i)(rural area|rural|gram)", full_text):
        criteria["rural_urban"] = "RURAL"
    elif re.search(r"(?i)(urban|city|metropol)", full_text):
        criteria["rural_urban"] = "URBAN"
    
    # Beneficiary type
    if re.search(r"(?i)(street vendor|artisan|widow|widow woman|farmer|agriculture)", full_text):
        if re.search(r"(?i)(street vendor)", full_text):
            criteria["beneficiary_scope"] = "STREET VENDOR"
        elif re.search(r"(?i)(artisan)", full_text):
            criteria["beneficiary_scope"] = "ARTISAN"
        elif re.search(r"(?i)(widow)", full_text):
            criteria["beneficiary_scope"] = "WIDOW"
    
    # Income limit patterns
    income_patterns = [
        r"income.*?(?:Rs\.?|INR|rupees?)\s+([0-9,]+)",
        r"(?:annual income|family income|income limit).*?([0-9,]+)",
    ]
    for pattern in income_patterns:
        matches = re.findall(pattern, full_text, re.IGNORECASE)
        if matches:
            criteria["income_limit"] = matches[0]
            break
    
    # Category
    if re.search(r"(?i)(SC|ST|OBC|scheduled caste|scheduled tribe)", full_text):
        criteria["caste_category"] = "YES - Social Categories mentioned"
    
    # Citizenship
    if re.search(r"(?i)(indian citizen|citizen of india|indian)", full_text):
        criteria["citizenship"] = "Indian Citizen required"
    
    # Education
    if re.search(r"(?i)(education|qualified|skill|training|literate)", full_text):
        criteria["education_required"] = "YES - See full details"
    
    # Marital status
    if re.search(r"(?i)(married|unmarried|widow|divorced|separated)", full_text):
        criteria["marital_status"] = "YES - See full details"
    
    # Find exclusion criteria
    lines = full_text.split('\n')
    for i, line in enumerate(lines):
        if re.search(r"(?i)(not eligible|excluded|shall not|ineligible|exclusion)", line):
            context_start = max(0, i - 1)
            context_end = min(len(lines), i + 5)
            exclusion_text = '\n'.join(lines[context_start:context_end])
            if exclusion_text.strip() not in [e["text"] for e in criteria["exclusion_paragraphs"]]:
                criteria["exclusion_paragraphs"].append({
                    "line_number": i + 1,
                    "text": exclusion_text.strip()
                })
    
    return criteria

def analyze_pdf(pdf_path: str, scheme_info: Dict[str, str]) -> Dict[str, Any]:
    """Analyze a single PDF for eligibility information."""
    
    result = {
        "scheme_id": scheme_info["scheme_id"],
        "scheme_name": scheme_info["scheme_name"],
        "pdf_filename": Path(pdf_path).name,
        "extraction_status": "STARTING",
        "full_pdf_content": None,
        "extracted_criteria": None,
        "summary": {}
    }
    
    try:
        # Extract full PDF content
        pdf_content = extract_pdf_content_with_context(pdf_path, max_pages=50)
        result["full_pdf_content"] = pdf_content
        
        # Extract criteria
        if "full_text" in pdf_content:
            criteria = extract_specific_criteria(
                pdf_content["full_text"],
                pdf_content.get("pages", [])
            )
            result["extracted_criteria"] = criteria
            
            # Generate summary
            summary = {
                "total_pages": pdf_content["total_pages"],
                "beneficiary_scope": criteria.get("beneficiary_scope") or "NOT EXTRACTED",
                "age_minimum": criteria.get("age_minimum") or "NOT FOUND",
                "age_maximum": criteria.get("age_maximum") or "NOT FOUND",
                "gender": criteria.get("gender") or "NOT SPECIFIED",
                "income_limit": criteria.get("income_limit") or "NOT FOUND",
                "rural_urban": criteria.get("rural_urban") or "NOT SPECIFIED",
                "citizenship": criteria.get("citizenship") or "NOT MENTIONED",
                "eligibility_sections_found": len(criteria["eligibility_paragraphs"]),
                "exclusion_criteria_found": len(criteria["exclusion_paragraphs"])
            }
            result["summary"] = summary
            result["extraction_status"] = "COMPLETED"
        else:
            result["extraction_status"] = "ERROR: No full text extracted"
            
    except Exception as e:
        result["extraction_status"] = f"ERROR: {str(e)}"
    
    return result

def main():
    """Main function."""
    data_dir = Path("data")
    results = {}
    
    print("=" * 80)
    print("ADVANCED GOVERNMENT SCHEME PDF ELIGIBILITY EXTRACTION")
    print("=" * 80)
    print()
    
    for pdf_filename, scheme_info in SCHEMES.items():
        pdf_path = data_dir / pdf_filename
        
        print(f"\n{'='*80}")
        print(f"Processing: {scheme_info['scheme_name']}")
        print(f"File: {pdf_filename}")
        print(f"{'='*80}")
        
        if not pdf_path.exists():
            print(f"ERROR: File not found - {pdf_path}")
            continue
        
        # Analyze the PDF
        analysis = analyze_pdf(str(pdf_path), scheme_info)
        results[scheme_info["scheme_id"]] = analysis
        
        # Print summary
        if analysis["extraction_status"] == "COMPLETED":
            print("\nEXTRACTION SUMMARY:")
            for key, value in analysis["summary"].items():
                print(f"  {key}: {value}")
        else:
            print(f"Status: {analysis['extraction_status']}")
    
    # Save results
    output_file = Path("pdf_advanced_extraction_results.json")
    with open(output_file, "w", encoding="utf-8") as f:
        # Convert to serializable format
        output_data = {}
        for scheme_id, data in results.items():
            output_data[scheme_id] = {
                "scheme_id": data["scheme_id"],
                "scheme_name": data["scheme_name"],
                "pdf_filename": data["pdf_filename"],
                "extraction_status": data["extraction_status"],
                "summary": data["summary"],
                "extracted_criteria": data["extracted_criteria"],
                # Include first 20 pages for manual review
                "pages_preview": data["full_pdf_content"]["pages"][:20] if data["full_pdf_content"] else []
            }
        
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n\n{'='*80}")
    print(f"Results saved to: {output_file}")
    print(f"{'='*80}\n")
    
    return results

if __name__ == "__main__":
    main()
