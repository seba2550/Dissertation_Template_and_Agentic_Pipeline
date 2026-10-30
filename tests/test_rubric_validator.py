"""
Unit tests for pipeline.rubric_validator.
Tests all UCSF Dissertation Rubric checks against conforming and non-conforming inputs.
"""

import unittest
import os
import tempfile
from pipeline.rubric_validator import RubricValidator, RubricCheckResult, RubricReport


class TestRubricValidator(unittest.TestCase):

    def test_real_master_dissertation_compliance(self):
        """Verifies that dissertation_master.tex (or dissertation_master_template.tex) passes 100% of required UCSF rubric checks."""
        master_tex = "dissertation_master.tex"
        if not os.path.isfile(master_tex):
            master_tex = "templates/latex/dissertation_master_template.tex"
        if not os.path.isfile(master_tex):
            self.skipTest("dissertation_master.tex not found in workspace")

        validator = RubricValidator(master_tex)
        report = validator.validate_all()

        # Print report summary if any failures for debugging
        if not report.is_compliant:
            for r in report.results:
                if not r.passed:
                    print(f"FAILED RULE: {r.rule_id} - {r.details}")

        self.assertTrue(report.is_compliant)
        self.assertEqual(report.failed_count, 0)
        self.assertGreaterEqual(report.passed_count, 19)

    def test_font_size_failure(self):
        """Violates 12pt requirement by setting 10pt."""
        dummy_tex = r"""
\documentclass[10pt]{report}
\usepackage{mathptmx}
\begin{document}
Hello
\end{document}
"""
        with tempfile.NamedTemporaryFile('w', suffix='.tex', delete=False) as f:
            f.write(dummy_tex)
            p = f.name
        try:
            val = RubricValidator(p)
            report = RubricReport()
            val._check_font_and_size(report)
            self.assertEqual(report.failed_count, 1)
            self.assertIn("12pt", report.results[0].details)
        finally:
            os.remove(p)

    def test_margin_failure(self):
        """Violates 1.0 inch margin requirement."""
        dummy_tex = r"""
\documentclass[12pt]{report}
\usepackage[letterpaper, top=0.5in, bottom=0.5in, left=1in, right=1in]{geometry}
\begin{document}
Hello
\end{document}
"""
        with tempfile.NamedTemporaryFile('w', suffix='.tex', delete=False) as f:
            f.write(dummy_tex)
            p = f.name
        try:
            val = RubricValidator(p)
            report = RubricReport()
            val._check_margins(report)
            self.assertEqual(report.failed_count, 1)
            self.assertIn("do not strictly specify 1-inch", report.results[0].details)
        finally:
            os.remove(p)

    def test_copyright_symbol_violation(self):
        """Violates rubric Sec III.B rule prohibiting copyright symbol (c)."""
        dummy_tex = r"""
\documentclass[12pt]{report}
\begin{document}
Copyright 2026 © by Author ALL RIGHTS RESERVED
\end{document}
"""
        with tempfile.NamedTemporaryFile('w', suffix='.tex', delete=False) as f:
            f.write(dummy_tex)
            p = f.name
        try:
            val = RubricValidator(p)
            report = RubricReport()
            val._check_copyright_page(report)
            self.assertEqual(report.failed_count, 1)
            self.assertIn("must NOT contain the copyright symbol", report.results[0].details)
        finally:
            os.remove(p)

    def test_sequential_order_inversion(self):
        """Violates rubric Sec II.A by placing Table of Contents before Abstract."""
        dummy_tex = r"""
\documentclass[12pt]{report}
\begin{document}
\tableofcontents
\clearpage
\chapter*{ABSTRACT}
\end{document}
"""
        with tempfile.NamedTemporaryFile('w', suffix='.tex', delete=False) as f:
            f.write(dummy_tex)
            p = f.name
        try:
            val = RubricValidator(p)
            report = RubricReport()
            val._check_sequential_order(report)
            self.assertEqual(report.failed_count, 1)
            self.assertIn("Ordering violation detected", report.results[0].details)
        finally:
            os.remove(p)

    def test_table_caption_position_violation(self):
        """Violates rubric Sec III.A.3 rule requiring table captions above table."""
        dummy_tex = r"""
\documentclass[12pt]{report}
\usepackage{caption}
\captionsetup[table]{position=below}
\begin{document}
Hello
\end{document}
"""
        with tempfile.NamedTemporaryFile('w', suffix='.tex', delete=False) as f:
            f.write(dummy_tex)
            p = f.name
        try:
            val = RubricValidator(p)
            report = RubricReport()
            val._check_table_captions_placement(report)
            self.assertEqual(report.failed_count, 1)
        finally:
            os.remove(p)

    def test_title_abbreviation_violation(self):
        """Violates rubric Sec I.C by having forbidden acronym in title."""
        dummy_tex = r"""
\documentclass[12pt]{report}
\begin{document}
\chapter*{ABSTRACT}
\doublespacing
\begin{center}
  \textbf{AN INVESTIGATION OF AD IN ADMIXED POPULATIONS}\\[0.1in]
  \textbf{JOHN DOE}
\end{center}
\end{document}
"""
        with tempfile.NamedTemporaryFile('w', suffix='.tex', delete=False) as f:
            f.write(dummy_tex)
            p = f.name
        try:
            val = RubricValidator(p)
            report = RubricReport()
            val._check_title_abbreviations(report)
            self.assertEqual(report.failed_count, 1)
            self.assertIn("Abbreviations detected in dissertation title", report.results[0].details)
        finally:
            os.remove(p)

    def test_publishing_agreement_unnumbered_violation(self):
        """Violates rubric Sec I.J by omitting pagecommand on publishing agreement includepdf."""
        dummy_tex = r"""
\documentclass[12pt]{report}
\begin{document}
\includepdf[pages={1}]{publishing_agreement_signed.pdf}
\end{document}
"""
        with tempfile.NamedTemporaryFile('w', suffix='.tex', delete=False) as f:
            f.write(dummy_tex)
            p = f.name
        try:
            val = RubricValidator(p)
            report = RubricReport()
            val._check_publishing_agreement(report)
            self.assertEqual(report.failed_count, 1)
            self.assertIn("lacks pagecommand", report.results[0].details)
        finally:
            os.remove(p)

    def test_abstract_formatting_violations(self):
        """Violates rubric Sec III.D when author name is Title Case and not ALL CAPS."""
        dummy_tex = r"""
\documentclass[12pt]{report}
\begin{document}
\chapter*{ABSTRACT}
\setstretch{1.2}
\begin{center}
  \textbf{TITLE OF DISSERTATION}\\[0.1in]
  \textbf{Sebastián Cruz-González}
\end{center}
\clearpage
\tableofcontents
\end{document}
"""
        with tempfile.NamedTemporaryFile('w', suffix='.tex', delete=False) as f:
            f.write(dummy_tex)
            p = f.name
        try:
            val = RubricValidator(p)
            report = RubricReport()
            val._check_abstract_rules(report)
            self.assertEqual(report.failed_count, 1)
            self.assertIn("student name must be in ALL CAPITAL LETTERS", report.results[0].details)
        finally:
            os.remove(p)

    def test_blockquotes_missing_singlespacing_violation(self):
        """Violates rubric Sec I.F & III.C when blockquotes lack single spacing."""
        dummy_tex = r"""
\documentclass[12pt]{report}
\begin{document}
\begin{quotation}
  This is a lengthy four-line quotation that is incorrectly double-spaced.
\end{quotation}
\end{document}
"""
        with tempfile.NamedTemporaryFile('w', suffix='.tex', delete=False) as f:
            f.write(dummy_tex)
            p = f.name
        try:
            val = RubricValidator(p)
            report = RubricReport()
            val._check_blockquotes(report)
            self.assertEqual(report.failed_count, 1)
            self.assertIn("single spacing configuration", report.results[0].details)
        finally:
            os.remove(p)

    def test_table_caption_after_tabular_violation(self):
        """Violates rubric Sec III.A when table caption is placed below tabular in document body."""
        dummy_tex = r"""
\documentclass[12pt]{report}
\usepackage{caption}
\captionsetup[table]{position=above, skip=6pt, font={small,singlespacing}, labelfont=bf}
\begin{document}
\begin{table}[ht]
  \begin{tabular}{cc}
    A & B \\
  \end{tabular}
  \caption{Misplaced Table Caption Below Tabular}
\end{table}
\end{document}
"""
        with tempfile.NamedTemporaryFile('w', suffix='.tex', delete=False) as f:
            f.write(dummy_tex)
            p = f.name
        try:
            val = RubricValidator(p)
            report = RubricReport()
            val._check_table_captions_placement(report)
            self.assertEqual(report.failed_count, 1)
            self.assertIn("places \\caption after tabular content", report.results[0].details)
        finally:
            os.remove(p)

    def test_figure_caption_before_graphic_violation(self):
        """Violates rubric Sec III.B when figure caption is placed above includegraphics."""
        dummy_tex = r"""
\documentclass[12pt]{report}
\usepackage{caption}
\captionsetup[figure]{position=below, skip=6pt, font={small,singlespacing}, labelfont=bf}
\begin{document}
\begin{figure}[ht]
  \caption{Misplaced Figure Caption Above Graphic}
  \includegraphics{figure.pdf}
\end{figure}
\end{document}
"""
        with tempfile.NamedTemporaryFile('w', suffix='.tex', delete=False) as f:
            f.write(dummy_tex)
            p = f.name
        try:
            val = RubricValidator(p)
            report = RubricReport()
            val._check_figure_captions_placement(report)
            self.assertEqual(report.failed_count, 1)
            self.assertIn("places \\caption before \\includegraphics graphic", report.results[0].details)
        finally:
            os.remove(p)

    def test_included_chapter_letter_suffix_violation(self):
        """Violates rubric Sec I.H when an included chapter uses prohibited letter suffix (e.g. Figure 2.1a)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            master = os.path.join(tmpdir, "master.tex")
            ch1 = os.path.join(tmpdir, "ch1.tex")
            with open(ch1, 'w') as f:
                f.write(r"\chapter{Test}\caption{Prohibited suffix \label{fig:21a}}")
            with open(master, 'w') as f:
                f.write(r"""
\documentclass[12pt]{report}
\begin{document}
\input{ch1}
\end{document}
""")
            val = RubricValidator(master)
            report = RubricReport()
            val._check_figure_and_table_numbering(report)
            self.assertEqual(report.failed_count, 1)
            self.assertIn("letter suffixes detected", report.results[0].details)

    def test_multiline_includepdf_publishing_agreement(self):
        """Verifies that multiline \\includepdf with pagecommand is correctly recognized."""
        dummy_tex = r"""
\documentclass[12pt]{report}
\begin{document}
\includepdf[
  pages={1},
  pagecommand={\thispagestyle{fancy}}
]{publishing_agreement_signed.pdf}
\end{document}
"""
        with tempfile.NamedTemporaryFile('w', suffix='.tex', delete=False) as f:
            f.write(dummy_tex)
            p = f.name
        try:
            val = RubricValidator(p)
            report = RubricReport()
            val._check_publishing_agreement(report)
            self.assertEqual(report.failed_count, 0)
            self.assertTrue(report.results[0].passed)
        finally:
            os.remove(p)

    def test_subfile_inclusion_and_comment_ignoring(self):
        """Verifies subfile resolution and that commented-out inputs are ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            master = os.path.join(tmpdir, "master.tex")
            active_ch = os.path.join(tmpdir, "active.tex")
            commented_ch = os.path.join(tmpdir, "commented.tex")

            with open(active_ch, 'w') as f:
                f.write(r"\chapter{Active Chapter}")
            with open(commented_ch, 'w') as f:
                f.write(r"\chapter{Prohibited}\caption{Violating Figure \label{fig:99a}}")

            with open(master, 'w') as f:
                f.write(r"""
\documentclass[12pt]{report}
\begin{document}
% \input{commented}
\subfile{active}
\end{document}
""")
            val = RubricValidator(master)
            # The commented file with prohibited suffix should not be included
            self.assertNotIn(commented_ch, val.included_files)
            self.assertIn(active_ch, val.included_files)
            report = RubricReport()
            val._check_figure_and_table_numbering(report)
            self.assertEqual(report.failed_count, 0)


if __name__ == "__main__":
    unittest.main()


