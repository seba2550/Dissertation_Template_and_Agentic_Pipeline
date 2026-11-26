"""
Tests for the ProQuest accessibility (PDF/UA-1) support: the veraPDF report parser, the static
source check in the rubric validator, the LuaLaTeX build command, \\FullPagePDF handling, and an
end-to-end template build checked with veraPDF when it is installed.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
import unicodedata

from pipeline.accessibility import parse_verapdf_xml, PROQUEST_RULES
from pipeline.compiler import LatexCompiler
from pipeline.rubric_validator import RubricValidator

VERAPDF_FAIL = """<?xml version="1.0" encoding="utf-8"?>
<report><jobs><job><validationReport jobEndStatus="normal" profileName="PDF/UA-1 validation profile"
 statement="PDF file is not compliant with Validation Profile requirements." isCompliant="false">
<details passedRules="96" failedRules="2" passedChecks="10" failedChecks="77">
<rule specification="ISO 14289-1:2014" clause="7.2" testNumber="2" status="failed" failedChecks="76">
<description>Natural language in the Outline entries shall be determined</description>
<check status="failed"><context>root/document[0]/Outlines[0](outline 48 0)</context></check></rule>
<rule specification="ISO 14289-1:2014" clause="7.1" testNumber="11" status="failed" failedChecks="1">
<description>The logical structure of the conforming file shall be described by a structure hierarchy</description>
<check status="failed"><context>root/document[0]</context></check></rule>
</details></validationReport></job></jobs></report>"""

VERAPDF_PASS = """<?xml version="1.0" encoding="utf-8"?>
<report><jobs><job><validationReport jobEndStatus="normal" isCompliant="true">
<details passedRules="106" failedRules="0" passedChecks="524795" failedChecks="0"></details>
</validationReport></job></jobs></report>"""

ACCESSIBLE_PREAMBLE = r"""\DocumentMetadata{lang=en-US, pdfversion=1.7, pdfstandard=ua-1, testphase={phase-III,math,table,title,firstaid}}
\documentclass[12pt,oneside]{report}
\usepackage[T1]{fontenc}
\usepackage{mathptmx}
\usepackage{hyperref}
\hypersetup{pdftitle={A Title}, pdfdisplaydoctitle=true}
\usepackage{ucsf-accessibility}
"""


def _write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _access_result(tex_path):
    report = RubricValidator(master_tex_path=tex_path).validate_all()
    return [r for r in report.results if r.rule_id == "IV.PROQUEST_ACCESSIBILITY"][0]


class TestVeraPdfParser(unittest.TestCase):

    def test_failures_use_proquest_titles(self):
        res = parse_verapdf_xml(VERAPDF_FAIL)
        self.assertFalse(res.compliant)
        self.assertEqual([(f.clause, f.test, f.count) for f in res.failures], [("7.2", "2", 76), ("7.1", "11", 1)])
        self.assertEqual(res.failures[0].proquest_title, "Bookmarks do not have a defined language.")
        self.assertEqual(res.failures[1].proquest_title, "Document tag tree is missing.")
        self.assertIn("root/document[0]", res.failures[1].examples)

    def test_compliant_report(self):
        res = parse_verapdf_xml(VERAPDF_PASS)
        self.assertTrue(res.compliant)
        self.assertEqual(res.failures, [])
        self.assertEqual(res.passed_checks, 524795)

    def test_all_ten_proquest_rules_have_fixes(self):
        # the ten rules of ProQuest's report for an untagged LaTeX PDF
        for key in [("7.1", "3"), ("7.1", "8"), ("7.1", "11"), ("7.2", "2"), ("7.21.7", "1"),
                    ("7.18.5", "1"), ("7.2", "34"), ("6.2", "1"), ("7.1", "10"), ("7.18.3", "1")]:
            self.assertIn(key, PROQUEST_RULES)


class TestCompilerUsesLuaLatex(unittest.TestCase):

    def test_latexmk_command_is_lualatex(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tex = os.path.join(tmpdir, "d.tex")
            _write(tex, "x")
            calls = []
            import pipeline.compiler as comp

            def fake_run(cmd, **kw):
                calls.append(cmd)
                return subprocess.CompletedProcess(cmd, 1, "", "")
            orig = comp.subprocess.run
            comp.subprocess.run = fake_run
            try:
                LatexCompiler(tex).compile()
                LatexCompiler(tex).compile(use_latexmk=False)
            finally:
                comp.subprocess.run = orig
            self.assertIn("-lualatex", calls[0])
            self.assertNotIn("-pdf", calls[0])
            self.assertEqual(calls[1][0], "lualatex")


class TestAccessibilitySourceCheck(unittest.TestCase):

    def test_template_passes(self):
        res = _access_result(os.path.join("templates", "latex", "dissertation_master_template.tex"))
        self.assertTrue(res.passed, res.details)

    def test_untagged_master_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tex = os.path.join(tmpdir, "m.tex")
            _write(tex, "\\documentclass[12pt]{report}\n\\usepackage{mathptmx}\n\\begin{document}\nx\n\\end{document}\n")
            res = _access_result(tex)
            self.assertFalse(res.passed)
            self.assertIn("DocumentMetadata", res.details)
            self.assertIn("ucsf-accessibility", res.details)
            self.assertIn("pdftitle", res.details)

    def test_commented_documentclass_does_not_hide_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tex = os.path.join(tmpdir, "m.tex")
            _write(tex, "% must come before \\documentclass\n" + ACCESSIBLE_PREAMBLE
                   + "\\begin{document}\nx\n\\end{document}\n")
            self.assertTrue(_access_result(tex).passed)

    def test_graphic_without_alt_text_is_reported(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tex = os.path.join(tmpdir, "m.tex")
            _write(os.path.join(tmpdir, "figure_alt_text.tex"), "\\FigAlt{fig_ok}{A described figure.}\n")
            _write(tex, ACCESSIBLE_PREAMBLE + "\\input{figure_alt_text}\n\\begin{document}\n"
                   "\\includegraphics[width=2in]{figures/fig_ok.pdf}\n\\includegraphics{figures/fig_missing.png}\n"
                   "\\end{document}\n")
            res = _access_result(tex)
            self.assertFalse(res.passed)
            self.assertIn("fig_missing", res.details)
            self.assertNotIn("fig_ok", res.details)

    def test_alt_text_keys_match_across_unicode_normalization(self):
        # macOS stores accented file names decomposed (NFD); keys are usually typed precomposed (NFC)
        with tempfile.TemporaryDirectory() as tmpdir:
            tex = os.path.join(tmpdir, "m.tex")
            nfd = unicodedata.normalize("NFD", "Title_Page_for_Sebastián")
            _write(os.path.join(tmpdir, "figure_alt_text.tex"),
                   "\\FigAlt{" + unicodedata.normalize("NFC", "Title_Page_for_Sebastián") + "}{Title page.}\n")
            _write(tex, ACCESSIBLE_PREAMBLE + "\\input{figure_alt_text}\n\\begin{document}\n"
                   "\\FullPagePDF{build_embedded/" + nfd + ".pdf}\n\\setcounter{page}{2}\n\\end{document}\n")
            self.assertTrue(_access_result(tex).passed)

    def test_includepdf_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tex = os.path.join(tmpdir, "m.tex")
            _write(tex, ACCESSIBLE_PREAMBLE + "\\FigAlt{Title_Page}{Title.}\n\\begin{document}\n"
                   "\\includepdf[pages={1}]{Title_Page.pdf}\n\\end{document}\n")
            res = _access_result(tex)
            self.assertFalse(res.passed)
            self.assertIn("FullPagePDF", res.details)


class TestFullPagePdfAgreement(unittest.TestCase):

    def _agreement(self, call):
        with tempfile.TemporaryDirectory() as tmpdir:
            tex = os.path.join(tmpdir, "m.tex")
            _write(tex, ACCESSIBLE_PREAMBLE + "\\newcommand{\\AgreementPageStyle}{fancy}\n\\begin{document}\n"
                   "\\printbibliography\n" + call + "\n\\end{document}\n")
            report = RubricValidator(master_tex_path=tex).validate_all()
            return [r for r in report.results if r.rule_id == "I.J_PUBLISHING_AGREEMENT"][0]

    def test_numbered_agreement(self):
        res = self._agreement("\\FullPagePDF[\\AgreementPageStyle]{publishing_agreement.pdf}")
        self.assertTrue(res.passed, res.details)

    def test_default_style_is_unnumbered_warning(self):
        res = self._agreement("\\FullPagePDF{publishing_agreement.pdf}")
        self.assertFalse(res.passed)
        self.assertEqual(res.severity, "WARNING")


@unittest.skipUnless(shutil.which("gs"), "Ghostscript not installed")
class TestEmbedFontsForms(unittest.TestCase):

    def test_forms_are_outlined(self):
        src = os.path.abspath(os.path.join("templates", "latex", "publishing_agreement.pdf"))
        script = os.path.abspath(os.path.join("agentic_scripts", "embed_fonts.sh"))
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out")
            res = subprocess.run(["bash", script, "-o", out, "--forms", src],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            self.assertEqual(res.returncode, 0, res.stdout)
            self.assertIn("outlined form: publishing_agreement.pdf", res.stdout)
            with open(os.path.join(out, "publishing_agreement.pdf"), "rb") as f:
                data = f.read()
            self.assertNotIn(b"/FontFile", data)  # no embedded fonts left: text is vector outlines


@unittest.skipUnless(shutil.which("latexmk") and shutil.which("lualatex") and shutil.which("verapdf"),
                     "latexmk, lualatex and verapdf needed")
class TestTemplateIsPdfUa(unittest.TestCase):

    def test_template_pdf_passes_pdfua1(self):
        from pipeline.accessibility import check_pdf_accessibility
        src = os.path.join("templates", "latex")
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ("dissertation_master_template.tex", "ch1_intro.tex", "references.bib",
                         "Title_Page.pdf", "publishing_agreement.pdf",
                         "ucsf-accessibility.sty", "figure_alt_text.tex", ".latexmkrc"):
                shutil.copy(os.path.join(src, name), tmpdir)
            subprocess.run(["latexmk", "-interaction=nonstopmode", "dissertation_master_template.tex"],
                           cwd=tmpdir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            res = check_pdf_accessibility(os.path.join(tmpdir, "dissertation_master_template.pdf"))
            self.assertTrue(res.compliant, [(f.clause, f.test, f.count) for f in res.failures])


if __name__ == "__main__":
    unittest.main()
