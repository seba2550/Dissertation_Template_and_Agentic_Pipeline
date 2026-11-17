"""
Tests for the rules back-ported from the finished dissertation (Nov 2026):
page-number distance, publishing agreement page style, bold references, float placement,
short last lines, embedded fonts, the output-overwrite guard, and sentence_case.py.
"""

import os
import subprocess
import sys
import tempfile
import unittest

from pipeline.cli import main
from pipeline.reference_extractor import guard_outputs, OutputExistsError
from pipeline.rubric_validator import RubricValidator, RubricReport
from pipeline.utils import find_unembedded_fonts
from tests.test_helpers import create_sample_docx

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _write(path: str, text: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _run_check(tex: str, check: str) -> RubricReport:
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "master.tex")
        with open(p, "w", encoding="utf-8") as f:
            f.write(tex)
        report = RubricReport()
        getattr(RubricValidator(p), check)(report)
        return report


PREAMBLE = "\\documentclass[12pt]{report}\n\\usepackage[letterpaper, top=1in, bottom=1in, left=1in, right=1in]{geometry}\n"


class TestPageNumberDistance(unittest.TestCase):
    def test_large_footskip_puts_number_too_close_to_edge(self):
        # The old template's value: 1in - 0.6in = 0.4in from the edge, below the 0.5in minimum.
        r = _run_check(PREAMBLE + "\\setlength{\\footskip}{0.6in}\n\\begin{document}\\end{document}",
                       "_check_footer_and_page_number_position")
        self.assertEqual(r.failed_count, 1)
        self.assertIn("0.40 in", r.results[0].details)

    def test_042in_footskip_passes(self):
        r = _run_check(PREAMBLE + "\\setlength{\\footskip}{0.42in}\n\\begin{document}\\end{document}",
                       "_check_footer_and_page_number_position")
        self.assertEqual(r.failed_count, 0)
        self.assertIn("0.58 in", r.results[0].details)

    def test_default_footskip_passes(self):
        r = _run_check(PREAMBLE + "\\begin{document}\\end{document}", "_check_footer_and_page_number_position")
        self.assertEqual(r.failed_count, 0)

    def test_pt_units(self):
        r = _run_check(PREAMBLE + "\\setlength{\\footskip}{50pt}\n\\begin{document}\\end{document}",
                       "_check_footer_and_page_number_position")
        self.assertEqual(r.failed_count, 1)


class TestPublishingAgreementStyle(unittest.TestCase):
    BODY = "\\begin{document}\n\\includepdf[pages={1}, pagecommand={\\thispagestyle{\\AgreementPageStyle}}]{publishing_agreement.pdf}\n\\end{document}"

    def test_macro_fancy_passes(self):
        r = _run_check(PREAMBLE + "\\newcommand{\\AgreementPageStyle}{fancy}\n" + self.BODY, "_check_publishing_agreement")
        self.assertEqual((r.passed_count, r.failed_count, r.warning_count), (1, 0, 0))

    def test_macro_empty_warns(self):
        r = _run_check(PREAMBLE + "\\newcommand{\\AgreementPageStyle}{empty}\n" + self.BODY, "_check_publishing_agreement")
        self.assertEqual((r.passed_count, r.failed_count, r.warning_count), (0, 0, 1))


class TestBoldReferences(unittest.TestCase):
    def _check(self, body, preamble=""):
        return _run_check(PREAMBLE + preamble + "\\begin{document}\n" + body + "\n\\end{document}",
                          "_check_bold_figure_table_references")

    def test_plain_ref_fails(self):
        self.assertEqual(self._check("As shown in Figure~\\ref{fig:a}.").failed_count, 1)

    def test_hand_typed_number_fails(self):
        r = self._check("Data are in Table 2.1 and Figure 3.6A.")
        self.assertEqual(r.failed_count, 1)
        self.assertIn("2 unbolded", r.results[0].details)

    def test_macros_and_bold_pass(self):
        self.assertEqual(self._check("See \\FIG[A]{a}, \\TABLE{b} and \\textbf{Figure~\\ref{fig:c}}.").failed_count, 0)

    def test_section_title_word_is_not_a_reference(self):
        self.assertEqual(self._check("\\section{Figure and Table Reference Example}").failed_count, 0)

    def test_cref_without_bold_format_fails(self):
        self.assertEqual(self._check("See \\cref{fig:a}.").failed_count, 1)

    def test_template_passes(self):
        report = RubricReport()
        RubricValidator(os.path.join(REPO, "templates/latex/dissertation_master_template.tex"))._check_bold_figure_table_references(report)
        self.assertEqual(report.failed_count, 0, report.results[0].details)


class TestFloatAndShortLines(unittest.TestCase):
    def test_float_page_option_warns(self):
        tex = PREAMBLE + "\\makeatletter\\def\\fps@figure{htb}\\def\\fps@table{htb}\\makeatother\n\\begin{document}\n\\begin{figure}[htbp]x\\end{figure}\n\\end{document}"
        r = _run_check(tex, "_check_float_placement")
        self.assertEqual(r.warning_count, 1)
        self.assertIn("[htbp]", r.results[0].details)

    def test_default_float_policy_missing_warns(self):
        r = _run_check(PREAMBLE + "\\begin{document}\\end{document}", "_check_float_placement")
        self.assertEqual(r.warning_count, 1)

    def test_short_last_lines_missing_warns(self):
        r = _run_check(PREAMBLE + "\\begin{document}\\end{document}", "_check_short_last_lines")
        self.assertEqual(r.warning_count, 1)

    def test_short_last_lines_configured_passes(self):
        tex = PREAMBLE + "\\brokenpenalty=10000\n\\setlength{\\parfillskip}{0pt plus 0.7\\linewidth}\n\\begin{document}\\end{document}"
        self.assertEqual(_run_check(tex, "_check_short_last_lines").passed_count, 1)


def _write_pdf(path: str, font_dict: bytes):
    """Minimal uncompressed one-page PDF whose page uses the given font dictionary."""
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        font_dict,
        b"<< /Length 35 >>\nstream\nBT /F1 12 Tf 72 720 Td (Hi) Tj ET\nendstream",
    ]
    out = b"%PDF-1.4\n"
    for i, o in enumerate(objs, 1):
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    out += b"trailer << /Root 1 0 R >>\n%%EOF\n"
    with open(path, "wb") as f:
        f.write(out)


class TestFontEmbedding(unittest.TestCase):
    def test_base14_reference_is_unembedded(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "r_figure.pdf")
            _write_pdf(p, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
            self.assertEqual(find_unembedded_fonts(p), ["Helvetica"])

    def test_descriptor_without_fontfile_is_unembedded(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "docusign.pdf")
            _write_pdf(p, b"<< /Type /Font /Subtype /TrueType /BaseFont /ArialMT /FontDescriptor << /Type /FontDescriptor /FontName /ArialMT /Flags 32 >> >>")
            self.assertEqual(find_unembedded_fonts(p), ["ArialMT"])

    def test_embedded_font_passes(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "ok.pdf")
            _write_pdf(p, b"<< /Type /Font /Subtype /TrueType /BaseFont /ABCDEF+ArialMT /FontDescriptor << /Type /FontDescriptor /FontName /ABCDEF+ArialMT /FontFile2 9 0 R >> >>")
            self.assertEqual(find_unembedded_fonts(p), [])


class TestOverwriteGuard(unittest.TestCase):
    BIB = "@article{a, title={x}}\n"

    def test_refuses_bib_with_entries(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "refs.bib")
            _write(p, self.BIB)
            with self.assertRaises(OutputExistsError):
                guard_outputs([p])
            self.assertEqual(_read(p), self.BIB)

    def test_empty_or_missing_outputs_are_fine(self):
        with tempfile.TemporaryDirectory() as d:
            empty = os.path.join(d, "empty.bib")
            _write(empty, "% header only\n")
            guard_outputs([empty, os.path.join(d, "new.bib"), None])

    def test_overwrite_backs_up_first(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "refs.bib")
            _write(p, self.BIB)
            guard_outputs([p], overwrite=True)
            backups = [f for f in os.listdir(d) if f.startswith("refs.bib.bak-")]
            self.assertEqual(len(backups), 1)
            self.assertEqual(_read(os.path.join(d, backups[0])), self.BIB)

    def test_output_equal_to_local_cache_always_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "refs.bib")
            with self.assertRaises(OutputExistsError):
                guard_outputs([p], protected=[p], overwrite=True)

    def test_cli_extract_refuses_and_leaves_bib_intact(self):
        with tempfile.TemporaryDirectory() as d:
            docx = os.path.join(d, "ms.docx")
            create_sample_docx(docx)
            bib = os.path.join(d, "dissertation_references.bib")
            _write(bib, self.BIB)
            ret = main(["extract-refs", docx, "-o", bib, "-d", os.path.join(d, "d.txt"), "-m", os.path.join(d, "m.json"), "-l"])
            self.assertEqual(ret, 2)
            self.assertEqual(_read(bib), self.BIB)

    def test_cli_convert_refuses_existing_chapter(self):
        with tempfile.TemporaryDirectory() as d:
            docx = os.path.join(d, "ms.docx")
            create_sample_docx(docx)
            tex = os.path.join(d, "ch1.tex")
            _write(tex, "\\chapter{Mine}\n")
            self.assertEqual(main(["convert-docx", docx, "-o", tex]), 2)
            self.assertEqual(_read(tex), "\\chapter{Mine}\n")


class TestSentenceCase(unittest.TestCase):
    def test_dry_run_leaves_file_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "r.bib")
            src = "@article{k, title={Genome-wide Methylation Profiles Reveal Quantitative Views of Human Aging Rates}}\n"
            _write(p, src)
            out = subprocess.run([sys.executable, os.path.join(REPO, "agentic_scripts/sentence_case.py"), p, "--dry-run"],
                                 capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertIn("quantitative views of human aging rates", out.stdout)
            self.assertEqual(_read(p), src)

    def test_rewrite_keeps_backup(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "r.bib")
            _write(p, "@article{k, title={DNA Methylation in African Americans}}\n")
            subprocess.run([sys.executable, os.path.join(REPO, "agentic_scripts/sentence_case.py"), p],
                           capture_output=True, text=True, check=True)
            self.assertIn("title={DNA methylation in {African} {Americans}}", _read(p))
            self.assertTrue(any(f.startswith("r.bib.bak-") for f in os.listdir(d)))


if __name__ == "__main__":
    unittest.main()
