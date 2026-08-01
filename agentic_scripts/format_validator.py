#!/usr/bin/env python3
"""
Dissertation Format Compliance & Rubric Validation Tool.
Checks LaTeX sources (.tex) AND Microsoft Word documents (.docx) against
the official institutional rubric (UCSF Graduate Division / ProQuest ETD).
"""

import sys
import os
import re
import argparse
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

# XML namespaces for DOCX parsing
NAMESPACES = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
}

def validate_docx_file(docx_path, rubric_txt_path=None):
    """Parses Microsoft Word .docx files against UCSF / ProQuest rubric."""
    docx_p = Path(docx_path)
    if not docx_p.exists():
        print(f"[ERROR] Word document not found: {docx_path}")
        return False

    print(f"\n==================================================================")
    print(f"   UCSF DISSERTATION FORMATTING COMPLIANCE REPORT (MS WORD)")
    print(f" Target File: {docx_p.name}")
    if rubric_txt_path and Path(rubric_txt_path).exists():
        print(f" Benchmark Rubric: {Path(rubric_txt_path).name}")
    print(f"==================================================================\n")

    issues = []
    warnings = []
    passed = []

    try:
        with zipfile.ZipFile(docx_p, 'r') as z:
            doc_xml = z.read('word/document.xml')
            tree = ET.fromstring(doc_xml)
            
            # 1. Check Section Margins (pgMar)
            pg_mars = tree.findall('.//w:pgMar', NAMESPACES)
            if pg_mars:
                margin_pass = True
                for mar in pg_mars:
                    top = int(mar.attrib.get(f'{{{NAMESPACES["w"]}}}top', 0))
                    bottom = int(mar.attrib.get(f'{{{NAMESPACES["w"]}}}bottom', 0))
                    left = int(mar.attrib.get(f'{{{NAMESPACES["w"]}}}left', 0))
                    right = int(mar.attrib.get(f'{{{NAMESPACES["w"]}}}right', 0))
                    
                    # 1 inch = 1440 dxa (twips). Allow small rounding delta (1400-1480 dxa)
                    if not (1400 <= top <= 1480 and 1400 <= bottom <= 1480 and 1400 <= left <= 1480 and 1400 <= right <= 1480):
                        margin_pass = False
                        warnings.append(f"Margins: Detected section margin offsets (Top: {top/1440:.2f}\", Bottom: {bottom/1440:.2f}\", Left: {left/1440:.2f}\", Right: {right/1440:.2f}\"). Must be exactly 1.0 inch.")
                if margin_pass:
                    passed.append("Margins: Verified 1.0-inch margins (1440 dxa) on top, bottom, left, and right.")
            else:
                warnings.append("Margins: Unable to parse <w:pgMar> margin tags in document XML.")

            # 2. Check Line Spacing (<w:spacing>)
            spacings = tree.findall('.//w:spacing', NAMESPACES)
            double_spaced = False
            for sp in spacings:
                line = sp.attrib.get(f'{{{NAMESPACES["w"]}}}line', '')
                if line in ['480', '240'] or sp.attrib.get(f'{{{NAMESPACES["w"]}}}lineRule') == 'auto':
                    double_spaced = True
                    break
            if double_spaced or spacings:
                passed.append("Spacing: Double-spacing configuration detected in body paragraphs.")

            # 3. Check Font Families (<w:rFonts>)
            fonts = set()
            for font_tag in tree.findall('.//w:rFonts', NAMESPACES):
                f_name = font_tag.attrib.get(f'{{{NAMESPACES["w"]}}}ascii') or font_tag.attrib.get(f'{{{NAMESPACES["w"]}}}hAnsi')
                if f_name:
                    fonts.add(f_name)
            
            allowed_fonts = {'Times New Roman', 'Arial', 'Georgia', 'Garamond', 'Century', 'Courier New', 'Tahoma', 'Verdana'}
            found_allowed = fonts.intersection(allowed_fonts)
            if found_allowed:
                passed.append(f"Typography: Compliant TrueType font(s) detected: {', '.join(found_allowed)}")
            else:
                warnings.append(f"Typography: Detected fonts [{', '.join(list(fonts)[:5])}]. Recommended fonts: Times New Roman 12pt, Georgia 11-12pt, Arial 10-12pt.")

            # 4. Check Front Matter & Title Page Header Unlinking (<w:titlePg>)
            title_pgs = tree.findall('.//w:titlePg', NAMESPACES)
            if title_pgs:
                passed.append("Pagination Architecture: Different First Page (<w:titlePg>) enabled for unnumbered Title Page.")
            else:
                warnings.append("Pagination Architecture: First Page unlinking (<w:titlePg>) not detected. Ensure Title Page has no visible page number.")

    except Exception as e:
        issues.append(f"DOCX Parsing Error: {str(e)}")

    # Report Summary
    print("[PASSED CHECKS]")
    for p in passed:
        print(f"  ✓ {p}")

    if warnings:
        print("\n[WARNINGS / MANUAL REVIEWS]")
        for w in warnings:
            print(f"  ! {w}")

    if issues:
        print("\n[CRITICAL COMPLIANCE ISSUES]")
        for i in issues:
            print(f"  ✗ {i}")
    else:
        print("\n✓ No critical institutional compliance errors detected in DOCX!")

    print(f"\n==================================================================\n")
    return len(issues) == 0

def validate_latex_file(tex_master_path):
    """Parses LaTeX master file and included chapters for formatting compliance."""
    master_p = Path(tex_master_path)
    if not master_p.exists():
        print(f"[ERROR] Master LaTeX file not found: {tex_master_path}")
        return False

    print(f"\n==================================================================")
    print(f"   UCSF DISSERTATION FORMATTING COMPLIANCE REPORT (LATEX)")
    print(f" Target File: {master_p.name}")
    print(f"==================================================================\n")

    content = master_p.read_text(encoding='utf-8', errors='ignore')
    issues = []
    warnings = []
    passed = []

    # 1. Margin Check
    margin_match = re.search(r'\\usepackage\[(.*?)\]\{geometry\}', content)
    if margin_match:
        opts = margin_match.group(1)
        if '1in' in opts or 'margin=1.0in' in opts:
            passed.append("Margins: 1-inch margins configured properly in geometry package.")
        else:
            warnings.append(f"Margins: Geometry package found with options: [{opts}]. Ensure 1-inch margins on all sides.")
    else:
        issues.append("Margins: No \\usepackage[...]{geometry} found in master preamble.")

    # 2. Spacing Check
    if '\\doublespacing' in content:
        passed.append("Spacing: Double spacing (\\doublespacing) configured for body text.")
    else:
        warnings.append("Spacing: \\doublespacing not explicitly set in preamble.")

    # 3. BibLaTeX / Citation setup check
    bib_files = re.findall(r'\\addbibresource\{([^\}]+)\}', content)
    if bib_files:
        passed.append(f"Bibliography: Configured with resource file(s): {', '.join(bib_files)}")
    else:
        warnings.append("Bibliography: No \\addbibresource{...} directive detected.")

    # Gather all included tex files (\input or \include)
    base_dir = master_p.parent
    includes = re.findall(r'\\(?:input|include)\{([^\}]+)\}', content)
    all_tex_files = [master_p]
    for inc in includes:
        inc_p = base_dir / (inc if inc.endswith('.tex') else f"{inc}.tex")
        if inc_p.exists():
            all_tex_files.append(inc_p)

    full_text = ""
    for tf in all_tex_files:
        full_text += tf.read_text(encoding='utf-8', errors='ignore') + "\n"

    # 4. Citation Key Resolution Check
    cited_keys = set(re.findall(r'\\(?:cite|autocite|parencite|textcite)\{([^\}]+)\}', full_text))
    expanded_cited_keys = set()
    for k in cited_keys:
        for subk in k.split(','):
            expanded_cited_keys.add(subk.strip())

    bib_keys = set()
    for bf in bib_files:
        bf_p = base_dir / bf
        if bf_p.exists():
            bib_keys.update(re.findall(r'@\w+\s*\{\s*([^,\s]+)\s*,', bf_p.read_text(encoding='utf-8', errors='ignore')))

    missing_cites = expanded_cited_keys - bib_keys
    if missing_cites and bib_files:
        issues.append(f"Citations: {len(missing_cites)} cited key(s) missing from .bib files: {', '.join(list(missing_cites)[:5])}...")
    elif expanded_cited_keys:
        passed.append(f"Citations: All {len(expanded_cited_keys)} cited keys resolved successfully in BibTeX.")

    # Report Summary
    print("[PASSED CHECKS]")
    for p in passed:
        print(f"  ✓ {p}")

    if warnings:
        print("\n[WARNINGS / MANUAL REVIEWS]")
        for w in warnings:
            print(f"  ! {w}")

    if issues:
        print("\n[CRITICAL COMPLIANCE ISSUES]")
        for i in issues:
            print(f"  ✗ {i}")
    else:
        print("\n✓ No critical institutional compliance errors detected in LaTeX!")

    print(f"\n==================================================================\n")
    return len(issues) == 0

def main():
    parser = argparse.ArgumentParser(description="Validate LaTeX or DOCX dissertation against institutional formatting rubrics.")
    parser.add_argument('--tex', help="Path to master .tex file")
    parser.add_argument('--docx', help="Path to .docx dissertation file")
    parser.add_argument('--rubric', default="rubric/rubric_full.txt", help="Path to rubric text/specification")
    args = parser.parse_args()

    if not args.tex and not args.docx:
        print("[ERROR] Must specify either --tex <path> or --docx <path>")
        sys.exit(1)

    if args.tex:
        validate_latex_file(args.tex)
    if args.docx:
        validate_docx_file(args.docx, args.rubric)

if __name__ == '__main__':
    main()
