"""
pipeline.accessibility
======================
Checks a compiled dissertation PDF the way ProQuest's accessibility review does: veraPDF with the
PDF/UA-1 profile (ProQuest's report cites the same clause and test numbers). Failures are reported
with ProQuest's wording and the fix that applies to this template.

veraPDF is a free, open-source validator: `brew install verapdf` (macOS) or https://verapdf.org.
"""

import shutil
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# (clause, test) -> (ProQuest's short title, fix in this template)
_SOURCE_FIX = ("Build from the template: \\DocumentMetadata{lang=en-US, pdfstandard=ua-1, ...} before "
               "\\documentclass, compiled with LuaLaTeX (latexmk -lualatex).")
PROQUEST_RULES: Dict[Tuple[str, str], Tuple[str, str]] = {
    ("7.1", "3"): ("Content is missing accessibility tagging.",
                   _SOURCE_FIX + " If only the title page or agreement fail, run embed_fonts.sh --forms on them "
                   "and include them with \\FullPagePDF."),
    ("7.1", "8"): ("Required PDF metadata is missing or invalid.", _SOURCE_FIX),
    ("7.1", "9"): ("Document title is missing from the metadata.",
                   "Set pdftitle={...} in \\hypersetup."),
    ("7.1", "10"): ("Document viewer title setting is missing.", "Set pdfdisplaydoctitle=true in \\hypersetup."),
    ("7.1", "11"): ("Document tag tree is missing.", _SOURCE_FIX),
    ("7.1", "1"): ("Artifact content found inside tagged content.",
                   "An included PDF carries its own tags: run embed_fonts.sh --forms on it and use \\FullPagePDF."),
    ("7.1", "2"): ("Tagged content found inside an artifact.",
                   "An included PDF carries its own tags: run embed_fonts.sh --forms on it and use \\FullPagePDF."),
    ("6.2", "1"): ("The PDF is not marked as a tagged document (MarkInfo).", _SOURCE_FIX),
    ("7.2", "2"): ("Bookmarks do not have a defined language.", "Add lang=en-US to \\DocumentMetadata."),
    ("7.2", "34"): ("Page text does not have a defined language.", "Add lang=en-US to \\DocumentMetadata."),
    ("7.3", "1"): ("Figure is missing alternative text.",
                   "Add a \\FigAlt entry for the graphic to figure_alt_text.tex."),
    ("7.18.1", "2"): ("Annotation is not tagged.", _SOURCE_FIX),
    ("7.18.3", "1"): ("Page uses an invalid tab order setting.", _SOURCE_FIX),
    ("7.18.5", "1"): ("Link annotation is tagged incorrectly.", _SOURCE_FIX),
    ("7.18.5", "2"): ("Link annotation has no alternate description.", _SOURCE_FIX),
    ("7.21.7", "1"): ("Text cannot be mapped to Unicode.",
                      "Usually a figure or form PDF with Word/DocuSign fonts: run embed_fonts.sh (with --forms for "
                      "the title page and agreement). In LaTeX text, load \\usepackage[T1]{fontenc}."),
    ("7.21.4.2", "2"): ("Embedded font subset is incomplete (CIDSet).",
                        "Usually Arial in the DocuSign title page or agreement: run embed_fonts.sh --forms on them."),
}


@dataclass
class AccessibilityFailure:
    clause: str
    test: str
    count: int
    description: str
    proquest_title: str
    fix: str
    examples: List[str] = field(default_factory=list)


@dataclass
class AccessibilityResult:
    available: bool
    compliant: bool = False
    failures: List[AccessibilityFailure] = field(default_factory=list)
    passed_checks: int = 0
    error: Optional[str] = None


def verapdf_available() -> bool:
    return shutil.which("verapdf") is not None


def parse_verapdf_xml(xml_text: str) -> AccessibilityResult:
    """Parses veraPDF's XML report (``verapdf --format xml``)."""
    root = ET.fromstring(xml_text)
    report = root.find(".//validationReport")
    if report is None:
        return AccessibilityResult(available=True, error="veraPDF report has no validationReport element")
    details = report.find("details")
    result = AccessibilityResult(available=True, compliant=report.get("isCompliant") == "true",
                                 passed_checks=int(details.get("passedChecks", 0)) if details is not None else 0)
    for rule in report.iter("rule"):
        if rule.get("status") != "failed":
            continue
        clause, test = rule.get("clause", ""), rule.get("testNumber", "")
        title, fix = PROQUEST_RULES.get((clause, test), ("", "See the veraPDF rule description."))
        desc_el = rule.find("description")
        examples = [c.text for c in rule.iter("context") if c.text][:3]
        result.failures.append(AccessibilityFailure(
            clause=clause, test=test, count=int(rule.get("failedChecks", 0)),
            description=(desc_el.text or "").strip() if desc_el is not None else "",
            proquest_title=title, fix=fix, examples=examples))
    result.failures.sort(key=lambda f: -f.count)
    return result


def check_pdf_accessibility(pdf_path: str, timeout: int = 1800) -> AccessibilityResult:
    """Runs veraPDF (PDF/UA-1 profile) on ``pdf_path``."""
    if not verapdf_available():
        return AccessibilityResult(available=False,
                                   error="veraPDF not found. Install it with `brew install verapdf` (macOS) "
                                         "or from https://verapdf.org, then rerun.")
    proc = subprocess.run(["verapdf", "--flavour", "ua1", "--format", "xml", "--maxfailuresdisplayed", "3", pdf_path],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout, check=False)
    if not proc.stdout.strip():
        return AccessibilityResult(available=True, error=f"veraPDF produced no report: {proc.stderr.strip()[:500]}")
    return parse_verapdf_xml(proc.stdout)


def print_accessibility_report(result: AccessibilityResult) -> None:
    if not result.available or result.error:
        print(f"[!] {result.error}")
        return
    if result.compliant:
        print(f"[✓] PDF/UA-1 compliant: {result.passed_checks} checks passed, 0 failed "
              "(the checks ProQuest's accessibility review runs).")
        return
    print(f"[!] Not PDF/UA-1 compliant: {len(result.failures)} rule(s) failed.")
    for f in result.failures:
        name = f.proquest_title or f.description
        print(f"\n  - [{f.clause}-{f.test}] {name}  ({f.count} instance(s))")
        print(f"      Fix: {f.fix}")
        for ex in f.examples[:2]:
            print(f"      e.g. {ex[:150]}")
