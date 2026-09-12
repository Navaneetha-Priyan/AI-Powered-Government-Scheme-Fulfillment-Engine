#!/usr/bin/env python3
"""
Comprehensive Government Scheme Eligibility Extraction
Reads PDF files and creates structured eligibility criteria documentation
"""

import fitz
import json
import re
from pathlib import Path
from typing import Dict, List, Any

def extract_all_text_by_page(pdf_path: str) -> List[Dict]:
    """Extract all text from PDF, organized by page."""
    pages = []
    try:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            pages.append({
                "page_number": page_num + 1,
                "text": text
            })
        doc.close()
    except Exception as e:
        print(f"Error reading PDF: {e}")
    return pages

def create_eligibility_report(pdf_path: str, scheme_info: Dict) -> Dict[str, Any]:
    """Create comprehensive eligibility report from PDF."""
    
    pages = extract_all_text_by_page(pdf_path)
    full_text = "\n".join([p["text"] for p in pages])
    
    report = {
        "scheme_id": scheme_info["scheme_id"],
        "scheme_name": scheme_info["scheme_name"],
        "pdf_file": Path(pdf_path).name,
        "total_pages": len(pages),
        "extraction_status": "COMPLETE",
        "sections": {}
    }
    
    # Find major sections in the PDF
    section_keywords = [
        ("objectives", r"(?i)(objective|aim|goal|purpose)"),
        ("eligibility_criteria", r"(?i)(eligibility|eligible|criteria|qualifications?|who can apply)"),
        ("beneficiary_scope", r"(?i)(beneficiary|target|who can|applicant|individual|family)"),
        ("age_restrictions", r"(?i)(age|years old|minimum age|maximum age)"),
        ("income_limits", r"(?i)(income|annual income|family income|income limit|income ceiling|rupees?|rs\.?)"),
        ("social_categories", r"(?i)(sc|st|obc|scheduled caste|scheduled tribe|caste|category|social)"),
        ("geographic_scope", r"(?i)(rural|urban|state|district|area|geographic|location|region)"),
        ("exclusion_criteria", r"(?i)(not eligible|excluded|shall not|ineligible|exclusion|disqualification)"),
        ("required_documents", r"(?i)(document|certificate|proof|submit|furnish|attach|require)"),
        ("education_requirements", r"(?i)(education|qualified|skill|training|literate|pass)"),
        ("gender_restrictions", r"(?i)(male|female|woman|women|mother|pregnant|widow)"),
        ("marital_status", r"(?i)(married|unmarried|widow|widower|divorced|separated|single)"),
        ("citizenship", r"(?i)(citizen|citizenship|indian citizen|nationality)"),
    ]
    
    # Extract text for each section
    lines = full_text.split('\n')
    
    for section_name, pattern in section_keywords:
        report["sections"][section_name] = {
            "found": False,
            "content": [],
            "page_references": []
        }
        
        # Find lines matching the pattern
        for i, line in enumerate(lines):
            if re.search(pattern, line) and len(line.strip()) > 5:
                # Find which page this line is on
                page_ref = "unknown"
                char_count = 0
                for page_idx, page in enumerate(pages):
                    char_count += len(page["text"])
                    if char_count >= sum(len(p["text"]) for p in pages[:i]):
                        page_ref = page_idx + 1
                        break
                
                # Extract context (this line and surrounding lines)
                context_start = max(0, i - 1)
                context_end = min(len(lines), i + 4)
                context_text = '\n'.join(lines[context_start:context_end])
                
                if context_text.strip() not in [c for c in report["sections"][section_name]["content"]]:
                    report["sections"][section_name]["content"].append(context_text.strip())
                    report["sections"][section_name]["page_references"].append(page_ref)
                    report["sections"][section_name]["found"] = True
    
    # Create summary
    report["summary"] = {
        "sections_with_content": sum(1 for s in report["sections"].values() if s["found"]),
        "total_sections_searched": len(section_keywords),
        "eligibility_content_lines": len(report["sections"]["eligibility_criteria"]["content"]),
        "exclusion_content_lines": len(report["sections"]["exclusion_criteria"]["content"]),
    }
    
    return report, pages

def main():
    """Main function."""
    schemes = {
        "PM_Street_Vendor_AtmaNirbhar_Nidhi_PM_SVANidhi_3.pdf": {
            "scheme_id": "PM-SVANidhi",
            "scheme_name": "PM Street Vendor AtmaNirbhar Nidhi - Street Vendors Scheme"
        },
        "PM_Vishwakarma_Yojana.pdf": {
            "scheme_id": "PM-Vishwakarma",
            "scheme_name": "PM Vishwakarma Yojana - Artisans Scheme"
        },
        "Pradhan_Mantri_Awas_Yojana_-_Urban_PMAY-U_2.pdf": {
            "scheme_id": "PMAY-U",
            "scheme_name": "Pradhan Mantri Awas Yojana - Urban Housing"
        },
        "Pradhan_Mantri_Matru_Vandana_Yojana_PMMVY.pdf": {
            "scheme_id": "PMMVY",
            "scheme_name": "Pradhan Mantri Matru Vandana Yojana - Maternity Benefit"
        }
    }
    
    data_dir = Path("data")
    all_reports = {}
    
    print("="*80)
    print("COMPREHENSIVE GOVERNMENT SCHEME ELIGIBILITY EXTRACTION")
    print("="*80)
    print()
    
    for pdf_filename, scheme_info in schemes.items():
        pdf_path = data_dir / pdf_filename
        
        print(f"\nProcessing: {scheme_info['scheme_name']}")
        print(f"File: {pdf_filename}")
        print("-" * 80)
        
        if not pdf_path.exists():
            print(f"ERROR: File not found - {pdf_path}")
            continue
        
        try:
            report, pages = create_eligibility_report(str(pdf_path), scheme_info)
            all_reports[scheme_info["scheme_id"]] = {
                "report": report,
                "pages_sample": pages[:30]  # Store first 30 pages as sample
            }
            
            print(f"✓ Extraction completed")
            print(f"  Pages found: {report['total_pages']}")
            print(f"  Sections with content: {report['summary']['sections_with_content']}/{report['summary']['total_sections_searched']}")
            print(f"  Eligibility lines: {report['summary']['eligibility_content_lines']}")
            print(f"  Exclusion lines: {report['summary']['exclusion_content_lines']}")
            
        except Exception as e:
            print(f"ERROR: {str(e)}")
    
    # Save detailed report
    output_file = Path("comprehensive_eligibility_report.json")
    
    # Prepare output data
    output_data = {}
    for scheme_id, data in all_reports.items():
        output_data[scheme_id] = {
            "report": data["report"],
            "pdf_content_sample": []
        }
        # Add page samples
        for page in data["pages_sample"]:
            output_data[scheme_id]["pdf_content_sample"].append({
                "page_number": page["page_number"],
                "text_preview": page["text"][:1000] if len(page["text"]) > 1000 else page["text"]
            })
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*80}")
    print(f"Comprehensive report saved to: {output_file}")
    print(f"{'='*80}\n")
    
    return all_reports

if __name__ == "__main__":
    main()
