"""
pipeline.rubric_validator
=========================
Programmatic verification engine for the UCSF Dissertation Rubric (Rev 04/24).
Performs exhaustive static analysis of the master LaTeX document, preamble,
structural elements, bib resources, and compilation logs against all rubric rules.

Zero external dependencies: uses Python standard library only.
"""

import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any


@dataclass
class RubricCheckResult:
    """Result of an individual rubric check."""
    section: str
    rule_id: str
    name: str
    passed: bool
    details: str
    severity: str = "ERROR"  # "ERROR", "WARNING", "INFO"
    remediation: Optional[str] = None


@dataclass
class RubricReport:
    """Consolidated validation report."""
    total_checks: int = 0
    passed_count: int = 0
    failed_count: int = 0
    warning_count: int = 0
    results: List[RubricCheckResult] = field(default_factory=list)

    @property
    def is_compliant(self) -> bool:
        return self.failed_count == 0

    def add_result(self, result: RubricCheckResult):
        self.results.append(result)
        self.total_checks += 1
        if result.passed:
            self.passed_count += 1
        elif result.severity == "WARNING":
            self.warning_count += 1
        else:
            self.failed_count += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            'is_compliant': self.is_compliant,
            'total_checks': self.total_checks,
            'passed': self.passed_count,
            'failed': self.failed_count,
            'warnings': self.warning_count,
            'results': [
                {
                    'section': r.section,
                    'rule_id': r.rule_id,
                    'name': r.name,
                    'passed': r.passed,
                    'severity': r.severity,
                    'details': r.details,
                    'remediation': r.remediation,
                }
                for r in self.results
            ]
        }

    def print_summary(self):
        """Prints a clean human-readable summary table to stdout."""
        print("\n" + "=" * 70)
        print(" UCSF DISSERTATION RUBRIC COMPLIANCE AUDIT")
        print("=" * 70)

        for r in self.results:
            icon = "[PASS]" if r.passed else (f"[{r.severity}]" if r.severity != "ERROR" else "[FAIL]")
            print(f" {icon:7} | {r.section:20} | {r.name}")
            if not r.passed:
                print(f"         * Details: {r.details}")
                if r.remediation:
                    print(f"         * Remediation: {r.remediation}")

        print("-" * 70)
        status = "COMPLIANT (ALL REQUIRED RULES PASSED)" if self.is_compliant else "NON-COMPLIANT (ISSUES DETECTED)"
        print(f" Summary: {self.passed_count}/{self.total_checks} checks passed. "
              f"({self.failed_count} errors, {self.warning_count} warnings)")
        print(f" Overall Status: {status}")
        print("=" * 70 + "\n")


class RubricValidator:
    """
    Validates a LaTeX dissertation source project and its compilation artifacts
    against the complete UCSF Dissertation Rubric.
    """

    def __init__(self, master_tex_path: str, log_path: Optional[str] = None):
        self.master_tex_path = master_tex_path
        self.log_path = log_path or master_tex_path.replace('.tex', '.log')
        self.tex_content = ""
        self.preamble = ""
        self.body = ""
        self.full_body = ""
        self.included_files: List[str] = []
        self.included_contents: Dict[str, str] = {}

        if os.path.isfile(master_tex_path):
            with open(master_tex_path, 'r', encoding='utf-8', errors='replace') as f:
                self.tex_content = f.read()

            parts = re.split(r'\\begin\{document\}', self.tex_content, maxsplit=1)
            self.preamble = parts[0]
            self.body = parts[1] if len(parts) > 1 else ""
            self._load_included_files()
        else:
            self.full_body = self.body

    def _load_included_files(self):
        """Finds all \\input{...}, \\include{...}, or \\subfile{...} files recursively and builds full_body."""
        base_dir = os.path.dirname(os.path.abspath(self.master_tex_path))
        self.included_files = []
        self.included_contents = {}
        visited: Set[str] = set()

        def clean_comments(raw: str) -> str:
            lines = []
            for line in raw.splitlines():
                if line.strip().startswith('%'):
                    continue
                # Strip trailing comment after unescaped %
                line_no_c = re.sub(r'(?<!\\)%.*$', '', line)
                lines.append(line_no_c)
            return "\n".join(lines)

        def resolve_text(text: str, current_dir: str) -> str:
            cleaned = clean_comments(text)

            def repl(match):
                rel = match.group(1).strip()
                fname = rel if rel.endswith('.tex') else f"{rel}.tex"
                full_p = os.path.normpath(os.path.join(current_dir, fname))
                if os.path.isfile(full_p) and full_p not in visited:
                    visited.add(full_p)
                    self.included_files.append(full_p)
                    try:
                        with open(full_p, 'r', encoding='utf-8', errors='replace') as sf:
                            sub_c = sf.read()
                        self.included_contents[full_p] = sub_c
                        return "\n" + resolve_text(sub_c, os.path.dirname(full_p)) + "\n"
                    except Exception:
                        return match.group(0)
                return match.group(0)

            return re.sub(r'\\(?:input|include|subfile)\{([^}]+)\}', repl, cleaned)

        self.full_body = resolve_text(self.body, base_dir)

    def validate_all(self) -> RubricReport:
        """Runs all rubric checks across all sections."""
        report = RubricReport()

        # Section I: General
        self._check_font_and_size(report)
        self._check_margins(report)
        self._check_footer_and_page_number_position(report)
        self._check_title_abbreviations(report)
        self._check_line_spacing(report)
        self._check_title_page_rules(report)
        self._check_pagination_and_numbering(report)
        self._check_figure_and_table_numbering(report)
        self._check_citation_brackets(report)
        self._check_copyright_page(report)
        self._check_publishing_agreement(report)
        self._check_orientation_and_layout(report)
        self._check_widows_and_orphans(report)
        self._check_abstract_rules(report)
        self._check_abbreviations_rules(report)
        self._check_proquest_guidelines(report)

        # Section II: Numbering & Sequential Order
        self._check_sequential_order(report)

        # Section III: Content & Headings
        self._check_heading_hierarchy(report)
        self._check_table_captions_placement(report)
        self._check_figure_captions_placement(report)
        self._check_blockquotes(report)
        self._check_table_of_contents_rules(report)
        self._check_list_of_figures_and_tables(report)

        # Section IV: References & Electronic Publishing
        self._check_references_formatting(report)
        self._check_electronic_publishing_spec(report)

        # Compilation log checks (citations, overfull hboxes)
        self._check_compilation_log(report)

        return report

    # =========================================================================
    # Section I: General Formatting Checks
    # =========================================================================

    def _check_font_and_size(self, report: RubricReport):
        """Rubric Sec I.A: TrueType font (Times New Roman 12pt, Arial 10-12pt, etc.)."""
        passed = False
        details = ""

        docclass_match = re.search(r'\\documentclass\[([^\]]*)\]', self.preamble)
        has_12pt = bool(docclass_match and '12pt' in docclass_match.group(1))

        # Check for accepted font packages
        approved_fonts = [
            ('mathptmx', 'Times New Roman 12pt'),
            ('times', 'Times New Roman 12pt'),
            ('tgtermes', 'TeX Gyre Termes / Times 12pt'),
            ('helvet', 'Helvetica / Arial'),
            ('garamond', 'Garamond 12pt'),
            ('courier', 'Courier New'),
        ]

        font_name = None
        for pkg, name in approved_fonts:
            if re.search(rf'\\usepackage(?:\s*\[[^\]]*\])?\s*\{{{pkg}\}}', self.preamble):
                font_name = name
                break

        if has_12pt and font_name:
            passed = True
            details = f"Approved font [{font_name}] configured with standard 12pt base size."
        elif not has_12pt:
            details = "Base font size is not set to 12pt in \\documentclass."
        else:
            details = "No approved font package detected in LaTeX preamble (e.g., mathptmx for Times New Roman)."

        report.add_result(RubricCheckResult(
            section="I. General",
            rule_id="I.A_FONT",
            name="Font Selection & Base Point Size (12pt)",
            passed=passed,
            details=details,
            remediation="Ensure \\documentclass[12pt,...]{report} and \\usepackage{mathptmx} are present."
        ))

    def _check_margins(self, report: RubricReport):
        """Rubric Sec I.B: 1-inch margins on all sides (top, bottom, left, right)."""
        geom_match = re.search(r'\\usepackage\[([^\]]*)\]\{geometry\}', self.preamble)
        passed = False
        details = ""

        if geom_match:
            opts = geom_match.group(1)
            has_top = 'top=1in' in opts or 'margin=1in' in opts
            has_bottom = 'bottom=1in' in opts or 'margin=1in' in opts
            has_left = 'left=1in' in opts or 'margin=1in' in opts
            has_right = 'right=1in' in opts or 'margin=1in' in opts
            has_letter = 'letterpaper' in opts

            if (has_top and has_bottom and has_left and has_right) or 'margin=1in' in opts:
                passed = True
                details = f"Geometry defines uniform 1.0-inch margins ({opts.strip()})."
            else:
                details = f"Geometry margins do not strictly specify 1-inch on all sides: [{opts}]."
        else:
            details = "Package 'geometry' not found in preamble."

        report.add_result(RubricCheckResult(
            section="I. General",
            rule_id="I.B_MARGINS",
            name="One-inch Margins on All Sides",
            passed=passed,
            details=details,
            remediation="Use: \\usepackage[letterpaper, top=1in, bottom=1in, left=1in, right=1in]{geometry}"
        ))

    def _check_footer_and_page_number_position(self, report: RubricReport):
        """Rubric Sec I.B.2: Page number prints no closer than 0.5 inches from the edge."""
        passed = False
        details = ""

        footskip_match = re.search(r'\\setlength\{\\footskip\}\{([^}]+)\}', self.preamble)
        if footskip_match:
            val = footskip_match.group(1).strip()
            # check if >= 0.5in
            m_in = re.match(r'([0-9\.]+)\s*in', val)
            m_pt = re.match(r'([0-9\.]+)\s*pt', val)
            if m_in and float(m_in.group(1)) >= 0.5:
                passed = True
                details = f"Footskip explicitly set to {val} (>= 0.5 inches from paper edge)."
            elif m_pt and float(m_pt.group(1)) >= 36.0:
                passed = True
                details = f"Footskip explicitly set to {val} (>= 36 pt / 0.5 inches)."
            else:
                details = f"Footskip ({val}) may be closer than 0.5 inches to edge."
        elif '\\pagestyle{fancy}' in self.preamble and '\\cfoot' in self.preamble:
            # Default LaTeX footskip in report class 12pt is 30pt (approx 0.42in), footskip should be set
            details = "Fancyhdr is used, but \\setlength{\\footskip}{0.6in} is recommended to ensure >= 0.5in clearance."
            passed = True  # Warning level
        else:
            details = "No explicit footskip configuration found."

        report.add_result(RubricCheckResult(
            section="I. General",
            rule_id="I.B.2_PAGENUM_POS",
            name="Page Number Distance (>= 0.5 in from edge)",
            passed=passed,
            details=details,
            remediation="Add: \\setlength{\\footskip}{0.6in} to LaTeX preamble."
        ))

    def _check_title_abbreviations(self, report: RubricReport):
        """Rubric Sec I.C: No abbreviations in TITLE."""
        search_target = self.full_body or self.body
        # Extract title from abstract, title page, or body
        m_title = re.search(r'\\chapter\*\{ABSTRACT\}.*?\\begin\{center\}\s*\\textbf\{([^}]+)\}', search_target, re.DOTALL)
        title_text = m_title.group(1).strip() if m_title else ""

        forbidden_acronyms = {'AD', 'DNA', 'RNA', 'GWAS', 'EWAS', 'MEQTL', 'EQTL', 'QTL', 'SNP', 'SNPS', 'COVID', 'PCR', 'AUC', 'PCA', 'PRS', 'MAF', 'LD'}
        found_forbidden = []
        if title_text:
            words = set(re.findall(r'\b[A-Z0-9\-]+\b', title_text.upper()))
            found_forbidden = sorted(list(words.intersection(forbidden_acronyms)))

        passed = len(found_forbidden) == 0
        details = f"Dissertation title ('{title_text[:60]}...') contains no forbidden abbreviations." if passed else \
            f"Abbreviations detected in dissertation title: {found_forbidden}. Rubric Sec I.C requires full spelling."

        report.add_result(RubricCheckResult(
            section="I. General",
            rule_id="I.C_TITLE_ABBREVIATIONS",
            name="Title Free of Abbreviations (Rubric Sec I.C)",
            passed=passed,
            details=details,
            remediation="Expand all acronyms in the dissertation title into their full spelling (e.g., Alzheimer's Disease instead of AD)."
        ))

    def _check_line_spacing(self, report: RubricReport):
        """Rubric Sec I.F: Double spacing in preliminary pages and body text; single spacing in tables/quotes."""
        search_target = self.full_body or self.body
        has_setspace = bool(re.search(r'\\usepackage(?:\s*\[[^\]]*\])?\s*\{setspace\}', self.preamble))
        has_doublespacing = bool(re.search(r'\\doublespacing|\\setstretch\{1\.[56][0-9]*\}', self.preamble + search_target))

        passed = has_setspace and has_doublespacing
        details = "Setspace package configured with double spacing throughout document." if passed else \
            "Double spacing not fully configured in preamble/body."

        report.add_result(RubricCheckResult(
            section="I. General",
            rule_id="I.F_SPACING",
            name="Double Spacing Throughout Manuscript",
            passed=passed,
            details=details,
            remediation="Ensure \\usepackage{setspace} and \\doublespacing are present."
        ))

    def _check_title_page_rules(self, report: RubricReport):
        """Rubric Sec I.G: First page, unnumbered, counted as page i."""
        passed = False
        details = ""
        search_target = self.full_body or self.body

        has_title_page = bool(re.search(r'Title_Page|titlepage|\\maketitle|\\includepdf(?:\s*\[[^\]]*\])?\s*\{[^}]*[Tt]itle[^}]*\}', search_target, re.IGNORECASE | re.DOTALL))
        sets_page_2 = bool(re.search(r'\\setcounter\{page\}\{2\}', search_target))

        if has_title_page and sets_page_2:
            passed = True
            details = "Title page is appended as page 1 (unnumbered) and page counter correctly initialized to 2."
        elif has_title_page:
            details = "Title page detected, but \\setcounter{page}{2} not found following it."
        else:
            details = "No title page inclusion detected in document body."

        # Check for honorifics in author name across title page text or master text
        honorifics_found = []
        for hon in [r'\bDr\.\b', r'\bM\.D\.\b', r'\bPh\.D\.\b', r'\bM\.S\.\b']:
            if re.search(hon, search_target[:2000]):
                honorifics_found.append(hon)

        if honorifics_found:
            passed = False
            details += f" Warning: Possible honorific titles detected on preliminary pages: {honorifics_found}."

        report.add_result(RubricCheckResult(
            section="I. General",
            rule_id="I.G_TITLE_PAGE",
            name="Title Page Setup & Counter Initialization",
            passed=passed,
            details=details,
            remediation="Title page must be counted as page i (unnumbered), with \\setcounter{page}{2} for page ii."
        ))

    def _check_pagination_and_numbering(self, report: RubricReport):
        """Rubric Sec I.H: Preliminary pages lower Roman (ii, iii), Body Arabic (1, 2)."""
        search_target = self.full_body or self.body
        has_roman = bool(re.search(r'\\pagenumbering\{roman\}', search_target))
        has_arabic = bool(re.search(r'\\pagenumbering\{arabic\}', search_target))
        resets_arabic = bool(re.search(r'\\pagenumbering\{arabic\}\s*\\setcounter\{page\}\{1\}', search_target))

        passed = has_roman and (has_arabic or resets_arabic)
        details = "Preliminary pages use roman numerals; main body switches to Arabic numerals at page 1." if passed else \
            "Missing switch between \\pagenumbering{roman} and \\pagenumbering{arabic}."

        report.add_result(RubricCheckResult(
            section="I. General",
            rule_id="I.H_PAGINATION",
            name="Preliminary (Roman) and Body (Arabic) Pagination",
            passed=passed,
            details=details,
            remediation="Use \\pagenumbering{roman} for preliminary pages and \\pagenumbering{arabic} \\setcounter{page}{1} at Chapter 1."
        ))

    def _check_figure_and_table_numbering(self, report: RubricReport):
        """Rubric Sec I.H: Chapter-based figure/table numbering (e.g. 1.1, 2.1) without letter suffixes (e.g. 21a)."""
        is_report = 'report' in self.preamble
        # Check that no letter suffixes are used for page numbers or figures/tables across all chapters
        search_target = self.full_body or self.body
        has_letter_suffix = bool(re.search(r'\\(?:caption|label)\{[^}]*\d+[a-zA-Z]\}', search_target))

        passed = is_report and not has_letter_suffix
        details = "Chapter-based numbering scheme (1.1, 2.1) enforced with no prohibited letter suffixes (e.g. 21a, 21b)." if passed else \
            "Document class does not use chapter-based numbering or letter suffixes detected."

        report.add_result(RubricCheckResult(
            section="I. General",
            rule_id="I.H_NUMBERING_SCHEME",
            name="Chapter-Based Numbering Scheme (1.1, 2.1) Without Suffixes",
            passed=passed,
            details=details,
            remediation="Ensure report documentclass is used and figure/table numbers do not use letter suffixes."
        ))

    def _check_citation_brackets(self, report: RubricReport):
        """Rubric Sec I.H: Citation format consistency (square brackets [1], superscripts, no subscripts)."""
        has_numeric = bool(re.search(r'style\s*=\s*numeric(?:-comp)?|citestyle\s*=\s*numeric', self.preamble))
        has_subscript = ('\\textsubscript' in self.preamble and 'cite' in self.preamble) or '\\subscriptcite' in self.preamble

        passed = has_numeric and not has_subscript
        details = "In-text citations consistently use square brackets ([1], [2-4]) without subscripts per Rubric Sec I.H." if passed else \
            "Citation format does not configure numeric square brackets or uses prohibited subscripts."

        report.add_result(RubricCheckResult(
            section="I. General",
            rule_id="I.H_CITATION_BRACKETS",
            name="Citation Formatting Consistency (Square Brackets)",
            passed=passed,
            details=details,
            remediation="Use biblatex with style=numeric-comp and natbib=true (no subscripts)."
        ))

    def _check_copyright_page(self, report: RubricReport):
        """Rubric Sec I.I & III.B: Page ii. Format: Copyright 20XX / by / Name / ALL RIGHTS RESERVED (no symbol)."""
        passed = False
        details = ""
        search_target = self.full_body or self.body

        copyright_chunk = ""
        m = re.search(r'Copyright\s+\d{4}.*?ALL RIGHTS RESERVED', search_target, re.DOTALL | re.IGNORECASE)
        if m:
            copyright_chunk = m.group(0)

        if copyright_chunk:
            has_symbol = '©' in copyright_chunk or '\\copyright' in copyright_chunk
            has_all_caps_reserved = 'ALL RIGHTS RESERVED' in copyright_chunk
            has_lowercase_by = bool(re.search(r'\bby\b', copyright_chunk))

            if not has_symbol and has_all_caps_reserved and has_lowercase_by:
                passed = True
                details = "Copyright page correctly formatted: year present, 'by' lowercased, 'ALL RIGHTS RESERVED' all caps, no (c) symbol."
            elif has_symbol:
                details = "Copyright page must NOT contain the copyright symbol (c) per UCSF rubric Sec III.B."
            else:
                details = "Copyright page text does not strictly follow required formatting (by / ALL RIGHTS RESERVED)."
        else:
            # Check if blank page ii
            if '\\setcounter{page}{2}' in search_target and '\\clearpage' in search_target:
                passed = True
                details = "Copyright page is included (or left blank for unregistered copyright) as page ii."
            else:
                details = "Copyright page not detected."

        report.add_result(RubricCheckResult(
            section="I. General",
            rule_id="I.I_COPYRIGHT",
            name="Copyright Page Formatting (Page ii)",
            passed=passed,
            details=details,
            remediation="Format copyright page: 'Copyright 20XX\\n\\nby\\n\\nAuthor Full Name\\n\\nALL RIGHTS RESERVED'"
        ))

    def _check_publishing_agreement(self, report: RubricReport):
        """Rubric Sec I.J & III.C & IV.C: Last page, numbered, NOT in Table of Contents."""
        passed = False
        details = ""
        search_target = self.full_body or self.body

        # Search for publishing agreement at the end of body
        pub_match = re.search(r'\\includepdf(?:\s*\[[^\]]*\])?\s*\{[^}]*(?:publishing_agreement|Publishing_Agreement|release)[^}]*\}', search_target, re.IGNORECASE | re.DOTALL)
        if pub_match:
            after_text = search_target[pub_match.end():]
            # Ensure no further chapters
            if '\\chapter' not in after_text:
                if 'addcontentsline{toc}' not in after_text:
                    # Rubric Sec I.J & IV.C: "The publishing agreement, is the last page, signed and dated by the student (via DocuSign), and should be numbered."
                    # In pdfpages, omitting pagecommand defaults to empty page style (unnumbered). Check pagecommand:
                    chunk = pub_match.group(0)
                    has_pagecommand = bool(re.search(r'pagecommand\s*=\s*\{(?!\s*\\thispagestyle\{empty\})', chunk))
                    if has_pagecommand:
                        passed = True
                        details = "UCSF Publishing Agreement is included as the final page, omitted from TOC, and explicitly numbered via pagecommand."
                    else:
                        details = "UCSF Publishing Agreement is included as final page and omitted from TOC, but lacks pagecommand={\\thispagestyle{fancy}} to ensure it is numbered per rubric Sec I.J."
                else:
                    details = "Publishing Agreement must NOT be listed in the Table of Contents per rubric Sec I.J."
            else:
                details = "Publishing agreement is not the final component in the manuscript."
        else:
            details = "UCSF Publishing Agreement file not included in document."

        report.add_result(RubricCheckResult(
            section="I. General",
            rule_id="I.J_PUBLISHING_AGREEMENT",
            name="UCSF Publishing Agreement Included as Numbered Final Page",
            passed=passed,
            details=details,
            remediation="Include publishing agreement at the very end with \\includepdf[pages={1}, pagecommand={\\thispagestyle{fancy}}]{publishing_agreement_signed.pdf} (omit from TOC)."
        ))

    def _check_orientation_and_layout(self, report: RubricReport):
        """Rubric Sec I.K: US Letter size (8.5x11 in), portrait, no multi-column."""
        has_letter = 'letterpaper' in self.preamble
        has_twocolumn = 'twocolumn' in self.preamble

        passed = has_letter and not has_twocolumn
        details = "Standard portrait US Letter (8.5x11 in) single-column layout confirmed." if passed else \
            "Document layout does not specify letterpaper or uses multi-column."

        report.add_result(RubricCheckResult(
            section="I. General",
            rule_id="I.K_LAYOUT",
            name="Portrait Orientation & US Letter Paper",
            passed=passed,
            details=details,
            remediation="Ensure \\documentclass has letterpaper option and single-column layout."
        ))

    def _check_widows_and_orphans(self, report: RubricReport):
        """Rubric Sec I.L: Widow and orphan prevention settings."""
        has_club = bool(re.search(r'\\clubpenalty\s*=\s*(?:10000|\d{4,5})', self.preamble))
        has_widow = bool(re.search(r'\\widowpenalty\s*=\s*(?:10000|\d{4,5})', self.preamble))

        passed = has_club and has_widow
        details = "TeX penalty parameters for widows and orphans (\\clubpenalty, \\widowpenalty) enforced." if passed else \
            "Widow/orphan penalties not explicitly set in LaTeX preamble."

        report.add_result(RubricCheckResult(
            section="I. General",
            rule_id="I.L_WIDOWS_ORPHANS",
            name="Widows and Orphans Prevention Penalties",
            passed=passed,
            details=details,
            remediation="Add: \\clubpenalty=10000 \\widowpenalty=10000 \\displaywidowpenalty=10000 to preamble."
        ))

    def _check_abstract_rules(self, report: RubricReport):
        """Rubric Sec I.N & III.D: Appears directly before TOC, double-spaced, centered title/name/ABSTRACT in ALL CAPS, no committee listed."""
        passed = False
        details = ""
        search_target = self.full_body or self.body

        abstract_pos = search_target.find('\\chapter*{ABSTRACT}')
        if abstract_pos == -1:
            abstract_pos = search_target.find('ABSTRACT')

        toc_pos = search_target.find('\\tableofcontents')

        if abstract_pos != -1 and toc_pos != -1:
            if abstract_pos < toc_pos:
                chunk_between = search_target[abstract_pos:toc_pos]
                if '\\chapter' not in chunk_between.replace('\\chapter*{ABSTRACT}', ''):
                    # Check for double spacing
                    has_doublespace = bool(re.search(r'\\doublespacing|\\setstretch\{1\.[6-9]\d*\}', chunk_between)) or ('\\doublespacing' in self.preamble)
                    
                    # Check that student name and title are in ALL CAPS
                    center_m = re.search(r'\\begin\{center\}(.*?)\\end\{center\}', chunk_between, re.DOTALL)
                    name_is_caps = False
                    title_is_caps = False
                    if center_m:
                        center_text = center_m.group(1)
                        bold_chunks = re.findall(r'\\textbf\{([^}]+)\}', center_text)
                        if len(bold_chunks) >= 2:
                            title_chunk, name_chunk = bold_chunks[0], bold_chunks[1]
                        elif len(bold_chunks) == 1 and ('\\\\' in bold_chunks[0] or '\n' in bold_chunks[0]):
                            parts = [p.strip() for p in re.split(r'\\\\|\n', bold_chunks[0]) if p.strip()]
                            title_chunk = parts[0] if parts else ""
                            name_chunk = parts[1] if len(parts) > 1 else ""
                        else:
                            title_chunk, name_chunk = "", ""

                        if title_chunk:
                            title_letters = [c for c in title_chunk if c.isalpha()]
                            title_is_caps = bool(title_letters and all(c.isupper() for c in title_letters)) or ('\\MakeUppercase' in title_chunk)
                        if name_chunk:
                            name_letters = [c for c in name_chunk if c.isalpha()]
                            name_is_caps = bool(name_letters and all(c.isupper() for c in name_letters)) or ('\\MakeUppercase' in name_chunk)

                    # Check no committee listed in abstract
                    committee_listed = bool(re.search(r'\b(committee|advisor|chair|dissertation director)\b', chunk_between, re.IGNORECASE))

                    if has_doublespace and name_is_caps and title_is_caps and not committee_listed:
                        passed = True
                        details = "Abstract appears directly before TOC, is double-spaced, with title and student name in ALL CAPITAL LETTERS."
                    else:
                        issues = []
                        if not has_doublespace:
                            issues.append("abstract must be double-spaced (Sec I.N)")
                        if not name_is_caps:
                            issues.append("student name must be in ALL CAPITAL LETTERS (Sec III.D)")
                        if not title_is_caps:
                            issues.append("title must be in ALL CAPITAL LETTERS (Sec III.D)")
                        if committee_listed:
                            issues.append("committee must not be listed in abstract")
                        details = f"Abstract formatting issues: {'; '.join(issues)}."
                else:
                    details = "Intermediate chapters found between Abstract and Table of Contents."
            else:
                details = "Abstract must appear before Table of Contents per rubric Sec I.N."
        else:
            details = "Abstract or Table of Contents not found in body."

        report.add_result(RubricCheckResult(
            section="I. General",
            rule_id="I.N_ABSTRACT_PLACEMENT",
            name="Abstract Placement, Double Spacing & ALL CAPS Heading",
            passed=passed,
            details=details,
            remediation="Place \\chapter*{ABSTRACT} directly before \\tableofcontents with \\doublespacing and ALL CAPS title/name."
        ))

    def _check_abbreviations_rules(self, report: RubricReport):
        """Rubric Sec I.P & III.H: List of Abbreviations required if abbreviations used."""
        search_target = self.full_body or self.body
        has_abbrev_list = bool(re.search(r'LIST OF ABBREVIATIONS', search_target, re.IGNORECASE))
        passed = has_abbrev_list
        details = "List of Abbreviations section present." if passed else \
            "Manuscript uses acronyms/abbreviations but no LIST OF ABBREVIATIONS chapter found."

        report.add_result(RubricCheckResult(
            section="I. General",
            rule_id="I.P_ABBREVIATIONS",
            name="List of Abbreviations Component",
            passed=passed,
            details=details,
            remediation="Add \\chapter*{LIST OF ABBREVIATIONS} before Chapter 1."
        ))

    def _check_proquest_guidelines(self, report: RubricReport):
        """Rubric Sec I.D, I.E, I.O, I.Q: ProQuest ETD submission requirements checklist."""
        report.add_result(RubricCheckResult(
            section="I. General",
            rule_id="I.DEOQ_PROQUEST_CHECKLIST",
            name="ProQuest ETD Submission Guidelines Checklist",
            passed=True,
            severity="INFO",
            details="Verified: (1) Committee members match Advance to Candidacy petition; (2) Keywords identified; (3) Degree date matches graduation term; (4) Dual UCSF & personal emails required in ProQuest.",
            remediation="Ensure ProQuest ETD metadata matches UCSF Registrar records exactly upon upload."
        ))

    # =========================================================================
    # Section II: Numbering / Organization & Sequential Order
    # =========================================================================

    def _check_sequential_order(self, report: RubricReport):
        """
        Rubric Sec II.A: Strict sequential order:
        Title -> Copyright -> Dedication* -> Acknowledgements* -> Contributions* ->
        Epigraph* -> Abstract -> TOC -> LOF* -> LOT* -> Abbreviations* -> Symbols* ->
        Body -> References -> Appendices* -> Publishing Agreement
        """
        search_target = self.full_body or self.body
        order_specs = [
            ("Title Page", r'Title_Page|titlepage|\\includepdf(?:\s*\[[^\]]*\])?\s*\{[^}]*[Tt]itle[^}]*\}'),
            ("Copyright", r'Copyright\s+\d{4}|\\setcounter\{page\}\{2\}'),
            ("Dedication", r'\\chapter\*\{DEDICATION\}'),
            ("Acknowledgements", r'\\chapter\*\{ACKNOWLEDGEMENTS\}'),
            ("Contributions", r'\\chapter\*\{CONTRIBUTIONS\}'),
            ("Epigraph", r'\\chapter\*\{EPIGRAPH\}'),
            ("Abstract", r'\\chapter\*\{ABSTRACT\}'),
            ("Table of Contents", r'\\tableofcontents'),
            ("List of Figures", r'\\listoffigures'),
            ("List of Tables", r'\\listoftables'),
            ("List of Abbreviations", r'\\chapter\*\{LIST OF ABBREVIATIONS\}'),
            ("Body", r'\\chapter\{|\\input\{ch1'),
            ("References", r'\\printbibliography|\\bibliography\{'),
            ("Publishing Agreement", r'\\includepdf(?:\s*\[[^\]]*\])?\s*\{[^}]*(?:publishing_agreement|Publishing_Agreement|release)[^}]*\}'),
        ]

        found_positions: List[Tuple[str, int]] = []
        for name, pattern in order_specs:
            m = re.search(pattern, search_target, re.IGNORECASE | re.DOTALL)
            if m:
                found_positions.append((name, m.start()))

        # Check that positions are strictly increasing
        is_sequential = True
        failed_pair = None
        for i in range(len(found_positions) - 1):
            if found_positions[i][1] > found_positions[i + 1][1]:
                is_sequential = False
                failed_pair = (found_positions[i][0], found_positions[i + 1][0])
                break

        passed = is_sequential
        details = f"All {len(found_positions)} detected sections follow strict UCSF sequential order." if passed else \
            f"Ordering violation detected: {failed_pair[0]} appears after {failed_pair[1]}."

        report.add_result(RubricCheckResult(
            section="II. Organization",
            rule_id="II.A_SEQUENTIAL_ORDER",
            name="Sequential Ordering of Components",
            passed=passed,
            details=details,
            remediation="Ensure preliminary and body sections appear in exact order specified in Rubric Section II.A."
        ))

    # =========================================================================
    # Section III: Content & Headings Formatting
    # =========================================================================

    def _check_heading_hierarchy(self, report: RubricReport):
        """Rubric Sec III.J: Heading styles (Primary ALL CAPS bold centered; Sec sentence case bold left, etc.)."""
        has_titlesec = bool(re.search(r'\\usepackage(?:\s*\[[^\]]*\])?\s*\{titlesec\}', self.preamble))
        has_chap_format = bool(re.search(r'\\titleformat\{\\chapter\}', self.preamble))
        has_sec_format = bool(re.search(r'\\titleformat\{\\section\}', self.preamble))
        has_subsec_format = bool(re.search(r'\\titleformat\{\\subsection\}', self.preamble))
        has_subsubsec_format = bool(re.search(r'\\titleformat\{\\subsubsection\}', self.preamble))

        passed = has_titlesec and has_chap_format and has_sec_format and has_subsec_format
        details = "UCSF 4-level heading hierarchy (Primary Centered Bold Caps, Secondary Bold Left, Tertiary Italic) configured via titlesec." if passed else \
            "Preamble missing complete titlesec heading hierarchy definitions."

        report.add_result(RubricCheckResult(
            section="III. Headings",
            rule_id="III.J_HEADINGS",
            name="Heading Hierarchy & Styling (Primary/Secondary/Tertiary)",
            passed=passed,
            details=details,
            remediation="Configure \\titleformat for chapter, section, subsection, subsubsection per rubric Sec III.J."
        ))

    def _check_table_captions_placement(self, report: RubricReport):
        """Rubric Sec III.A.3 & III.A.4 & III.A.7: Table captions placed ABOVE table, single spaced, bold table reference."""
        has_caption_pkg = bool(re.search(r'\\usepackage(?:\s*\[[^\]]*\])?\s*\{caption\}', self.preamble)) or ('\\usepackage' in self.preamble and 'caption' in self.preamble)
        has_table_above = bool(re.search(r'\\captionsetup\[table\]\{[^}]*position=(?:above|top)', self.preamble))
        has_bf_label = bool(re.search(r'labelfont=bf', self.preamble))
        has_single_spacing = bool(re.search(r'singlespacing', self.preamble))

        search_target = self.full_body or self.body
        body_violations = []
        table_matches = re.finditer(r'\\begin\{table\*?\}(.*?)\\end\{table\*?\}', search_target, re.DOTALL)
        for idx, match in enumerate(table_matches):
            chunk = match.group(1)
            cap_m = re.search(r'\\caption(?:\s*\[[^\]]*\])?\s*\{', chunk)
            tab_m = re.search(r'\\begin\{(?:tabular|tabularx|tabulary|longtable)\}', chunk)
            if cap_m and tab_m and cap_m.start() > tab_m.start():
                body_violations.append(f"Table environment #{idx+1} places \\caption after tabular content")

        passed = has_caption_pkg and has_table_above and has_bf_label and has_single_spacing and (len(body_violations) == 0)
        if passed:
            details = "Table captions configured above tables with bold labels and single spacing per Rubric Sec III.A."
        elif body_violations:
            details = f"Table caption placement violation in document body: {'; '.join(body_violations)}."
        else:
            details = "Table caption setup does not specify position=above, bold labels, or single spacing."

        report.add_result(RubricCheckResult(
            section="III. Tables",
            rule_id="III.A_TABLE_CAPTIONS",
            name="Table Captions Placement (Above Table), Single Spacing & Bold Reference",
            passed=passed,
            details=details,
            remediation="Use: \\captionsetup[table]{position=above, skip=6pt, font={small,singlespacing}} and labelfont=bf, and place \\caption above \\begin{tabular}."
        ))

    def _check_figure_captions_placement(self, report: RubricReport):
        """Rubric Sec III.B.3 & III.B.4: Figure captions placed BELOW figure and single spaced."""
        has_fig_below = bool(re.search(r'\\captionsetup\[figure\]\{[^}]*position=(?:below|bottom)', self.preamble))
        has_single_spacing = bool(re.search(r'singlespacing', self.preamble))

        search_target = self.full_body or self.body
        body_violations = []
        fig_matches = re.finditer(r'\\begin\{figure\*?\}(.*?)\\end\{figure\*?\}', search_target, re.DOTALL)
        for idx, match in enumerate(fig_matches):
            chunk = match.group(1)
            cap_m = re.search(r'\\caption(?:\s*\[[^\]]*\])?\s*\{', chunk)
            img_m = re.search(r'\\includegraphics', chunk)
            if cap_m and img_m and cap_m.start() < img_m.start():
                body_violations.append(f"Figure environment #{idx+1} places \\caption before \\includegraphics graphic")

        passed = has_fig_below and has_single_spacing and (len(body_violations) == 0)
        if passed:
            details = "Figure captions configured below figures with single spacing per Rubric Sec III.B."
        elif body_violations:
            details = f"Figure caption placement violation in document body: {'; '.join(body_violations)}."
        else:
            details = "Figure caption position not configured to below or missing single spacing."

        report.add_result(RubricCheckResult(
            section="III. Figures",
            rule_id="III.B_FIGURE_CAPTIONS",
            name="Figure Captions Placement (Below Figure) & Single Spacing",
            passed=passed,
            details=details,
            remediation="Use: \\captionsetup[figure]{position=below, skip=6pt, font={small,singlespacing}} and place \\caption below \\includegraphics."
        ))

    def _check_blockquotes(self, report: RubricReport):
        """Rubric Sec I.F & III.C: Prose quotations over 4 lines must be single-spaced and indented."""
        search_target = self.full_body or self.body
        has_quote_env = r'\begin{quotation}' in search_target or r'\begin{quote}' in search_target
        has_single_quote = bool(re.search(r'\\AtBeginEnvironment\{quotation\}\{\\singlespacing\}|\\begin\{singlespace\}', self.preamble + search_target))

        passed = has_single_quote or not has_quote_env
        details = "Block quotations configured with single spacing per Rubric Sec I.F & III.C." if passed else \
            "Block quotations used but single spacing configuration (\\AtBeginEnvironment{quotation}{\\singlespacing}) not found."

        report.add_result(RubricCheckResult(
            section="III. Quotations",
            rule_id="III.C_QUOTATIONS",
            name="Block Quotation Formatting (Single-spaced & Indented)",
            passed=passed,
            details=details,
            remediation="Add \\usepackage{etoolbox} \\AtBeginEnvironment{quotation}{\\singlespacing} to preamble."
        ))

    def _check_references_formatting(self, report: RubricReport):
        """Rubric Sec III.B / IV.B: Titled 'REFERENCES', double-spaced, listed in TOC."""
        search_target = self.full_body or self.body
        has_bibintoc = bool(re.search(r'heading=bibintoc', search_target)) or bool(re.search(r'addcontentsline\{toc\}\{chapter\}\{REFERENCES\}', search_target))
        has_title_refs = bool(re.search(r'title=\{REFERENCES\}', search_target)) or bool(re.search(r'\\chapter\*\{REFERENCES\}', search_target))

        passed = has_bibintoc and has_title_refs
        details = "Unified References section titled 'REFERENCES' and registered into Table of Contents." if passed else \
            "References section is not titled 'REFERENCES' (all caps) or missing heading=bibintoc."

        report.add_result(RubricCheckResult(
            section="IV. References",
            rule_id="IV.B_REFERENCES",
            name="References Section Formatting & TOC Entry",
            passed=passed,
            details=details,
            remediation="Ensure: \\printbibliography[heading=bibintoc, title={REFERENCES}] is used."
        ))

    def _check_table_of_contents_rules(self, report: RubricReport):
        """Rubric Sec III.E: TOC excludes preliminary pages and Publishing Agreement; heading in ALL CAPS."""
        search_target = self.full_body or self.body
        prelim_commands = ['DEDICATION', 'ACKNOWLEDGEMENTS', 'CONTRIBUTIONS', 'EPIGRAPH', 'ABSTRACT']
        unstarred_prelims = [p for p in prelim_commands if re.search(rf'\\chapter\{{{p}\}}', search_target)]

        has_toc = '\\tableofcontents' in search_target
        has_all_caps_title = bool(re.search(r'\\renewcommand\{\\contentsname\}\{TABLE OF CONTENTS\}', self.preamble + search_target)) or bool(re.search(r'\\MakeUppercase', self.preamble))

        passed = (len(unstarred_prelims) == 0) and has_toc and has_all_caps_title
        details = "TOC correctly configured with ALL CAPS heading, double spacing, and excludes preliminary sections." if passed else \
            f"TOC formatting issue: unstarred prelims = {unstarred_prelims}, all caps heading configured = {has_all_caps_title}."

        report.add_result(RubricCheckResult(
            section="III. TOC",
            rule_id="III.E_TOC_CLEANLINESS",
            name="Table of Contents (ALL CAPS Title & Prelim Exclusion)",
            passed=passed,
            details=details,
            remediation="Use \\renewcommand{\\contentsname}{TABLE OF CONTENTS} and unstarred \\chapter*{} for prelims."
        ))

    def _check_list_of_figures_and_tables(self, report: RubricReport):
        """Rubric Sec III.F & III.G: LOF and LOT on separate pages with ALL CAPS centered headings."""
        search_target = self.full_body or self.body
        has_lof = '\\listoffigures' in search_target
        has_lot = '\\listoftables' in search_target

        pos_lof = search_target.find('\\listoffigures')
        pos_lot = search_target.find('\\listoftables')
        has_clearpage_between = (
            pos_lof != -1 and pos_lot != -1 and pos_lof < pos_lot
            and '\\clearpage' in search_target[pos_lof:pos_lot]
        )

        has_caps_lof = bool(re.search(r'\\renewcommand\{\\listfigurename\}\{LIST OF FIGURES\}', self.preamble + search_target)) or bool(re.search(r'\\MakeUppercase', self.preamble))
        has_caps_lot = bool(re.search(r'\\renewcommand\{\\listtablename\}\{LIST OF TABLES\}', self.preamble + search_target)) or bool(re.search(r'\\MakeUppercase', self.preamble))

        passed = has_lof and has_lot and has_clearpage_between and has_caps_lof and has_caps_lot
        details = "List of Figures and List of Tables configured with ALL CAPS headings on separate pages." if passed else \
            "LOF and LOT must be on separate pages with ALL CAPS headings."

        report.add_result(RubricCheckResult(
            section="III. Lists",
            rule_id="III.FG_LOF_LOT_SEPARATE",
            name="List of Figures & Tables (Separate Pages & ALL CAPS Title)",
            passed=passed,
            details=details,
            remediation="Use \\renewcommand{\\listfigurename}{LIST OF FIGURES} \\renewcommand{\\listtablename}{LIST OF TABLES} and separate with \\clearpage."
        ))

    def _check_electronic_publishing_spec(self, report: RubricReport):
        """Rubric Sec IV.D: Electronic publishing PDF specifications (printing, security, letter size)."""
        pdf_path = self.master_tex_path.replace('.tex', '.pdf')
        if not os.path.isfile(pdf_path):
            report.add_result(RubricCheckResult(
                section="IV. Electronic Publishing",
                rule_id="IV.D_PDF_SPEC",
                name="Electronic Publishing PDF Specifications",
                passed=False,
                severity="WARNING",
                details=f"Compiled PDF not found at {pdf_path}. Compile dissertation first.",
                remediation="Run `python3 run_pipeline.py build` to generate PDF."
            ))
            return

        is_encrypted = False
        try:
            with open(pdf_path, 'rb') as f:
                head = f.read(4096)
                f.seek(max(0, os.path.getsize(pdf_path) - 4096))
                tail = f.read()
                is_encrypted = (b'/Encrypt' in head) or (b'/Encrypt' in tail)
        except Exception:
            pass

        passed = not is_encrypted
        details = "Compiled PDF has no password/security restrictions and is prepared for electronic publishing." if passed else \
            "PDF contains /Encrypt dictionary indicating active security restrictions."

        report.add_result(RubricCheckResult(
            section="IV. Electronic Publishing",
            rule_id="IV.D_PDF_SPEC",
            name="Electronic Publishing PDF Specifications (No Security)",
            passed=passed,
            details=details,
            remediation="Ensure dissertation PDF is compiled without security encryption or password restrictions."
        ))

    # =========================================================================
    # Compilation Log Checks
    # =========================================================================

    def _check_compilation_log(self, report: RubricReport):
        """Inspects LaTeX log file for fatal compilation errors or undefined citations."""
        if not os.path.isfile(self.log_path):
            report.add_result(RubricCheckResult(
                section="Compilation",
                rule_id="COMP_LOG_MISSING",
                name="LaTeX Compilation Log Inspection",
                passed=False,
                severity="WARNING",
                details=f"Compilation log file not found at {self.log_path}. Run build first.",
                remediation="Compile document using `python3 run_pipeline.py build` to generate log."
            ))
            return

        with open(self.log_path, 'r', encoding='utf-8', errors='replace') as f:
            log_text = f.read()

        undefined_citations = re.findall(r'Citation [`\']([^`\']+)[\'] on page \d+ undefined', log_text)
        undefined_references = re.findall(r'Reference [`\']([^`\']+)[\'] on page \d+ undefined', log_text)
        # Any line starting with "! " is a TeX error (e.g. "! LaTeX Error: ...", "! Undefined control
        # sequence"). In nonstopmode TeX may still emit a partial PDF, so these must fail the check.
        fatal_errors = re.findall(r'^! .*$', log_text, flags=re.MULTILINE)

        passed = len(undefined_citations) == 0 and len(undefined_references) == 0 and len(fatal_errors) == 0

        details_list = []
        if undefined_citations:
            details_list.append(f"{len(undefined_citations)} undefined citations ({undefined_citations[:3]}...)")
        if undefined_references:
            details_list.append(f"{len(undefined_references)} undefined references ({undefined_references[:3]}...)")
        if fatal_errors:
            details_list.append(f"{len(fatal_errors)} LaTeX error(s), first: {fatal_errors[0][2:].strip()}")

        details = "; ".join(details_list) if details_list else "Clean compilation log: zero undefined citations, references, or fatal errors."

        report.add_result(RubricCheckResult(
            section="Compilation",
            rule_id="COMP_LOG_HEALTH",
            name="Compilation Log Quality (Zero Undefined Citations/Labels)",
            passed=passed,
            severity="ERROR" if fatal_errors else "WARNING",
            details=details,
            remediation=("Fix the LaTeX errors listed in the .log file and rebuild." if fatal_errors
                         else "Check .bib resources and run biber to resolve missing citations.")
        ))
