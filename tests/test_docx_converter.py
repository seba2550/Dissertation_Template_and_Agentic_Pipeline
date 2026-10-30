"""
Unit tests for pipeline.docx_converter.
"""

import unittest
import os
import tempfile
from pipeline.docx_converter import DocxConverter, convert_docx_to_latex
from tests.test_helpers import create_sample_docx


class TestDocxConverter(unittest.TestCase):

    def test_convert_fixture_docx(self):
        """Tests complete conversion of a sample DOCX into rubric-compliant LaTeX."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sample_docx = os.path.join(tmpdir, "sample.docx")
            create_sample_docx(sample_docx)

            cmap = {
                "rId1": "Horvath2013",
                "rId2": "Smith2024",
                "10.1016/j.cell.2020.01.001": "Cell2020",
            }
            converter = DocxConverter(citation_map=cmap)
            out_tex = os.path.join(tmpdir, "out_chapter.tex")

            latex_out = converter.convert(
                docx_path=sample_docx,
                output_tex=out_tex,
                as_chapter=True,
                chapter_title="Epigenetics of Aging",
                chapter_label="ch:epigenetics",
            )

            self.assertTrue(os.path.isfile(out_tex))
            self.assertIn(r"\chapter{Epigenetics of Aging}", latex_out)
            self.assertIn(r"\label{ch:epigenetics}", latex_out)
            self.assertIn(r"\cite{Horvath2013}", latex_out)
            self.assertIn(r"\cite{Smith2024}", latex_out)
            self.assertIn(r"\subsection{Methods and statistical procedures}", latex_out)
            self.assertIn(r"\begin{quotation}", latex_out)
            self.assertIn(r"\begin{singlespace}", latex_out)
            self.assertIn(r"\section{Discussion and future perspectives}", latex_out)

    def test_citation_mapping_clean_doi_resolution(self):
        """Verifies clean_doi normalization inside _format_runs does not throw NameError."""
        cmap = {
            "10.1038/nature99999": "NatureKey2025",
        }
        converter = DocxConverter(citation_map=cmap)
        runs = [
            {'text': 'Found in literature ', 'bold': False, 'italic': False, 'r_id': None},
            {'text': '[1]', 'bold': False, 'italic': False, 'r_id': 'rId5'},
        ]
        # Target is a full URL, but map only has the bare DOI
        rel_map = {'rId5': 'https://doi.org/10.1038/nature99999'}
        formatted = converter._format_runs(runs, rel_map)
        self.assertIn(r"\cite{NatureKey2025}", formatted)

    def test_citation_mapping_replacement(self):
        """Test converting with a directly mapped citation key."""
        cmap = {
            "10.1038/nature12345": "Smith2024",
            "https://doi.org/10.1038/nature12345": "Smith2024",
        }
        converter = DocxConverter(citation_map=cmap)
        runs = [
            {'text': 'According to previous work ', 'bold': False, 'italic': False, 'r_id': None},
            {'text': '[1]', 'bold': False, 'italic': False, 'r_id': 'rId1'},
            {'text': ', methylation changes with age.', 'bold': False, 'italic': False, 'r_id': None},
        ]
        rel_map = {'rId1': 'https://doi.org/10.1038/nature12345'}
        formatted = converter._format_runs(runs, rel_map)
        self.assertIn(r"\cite{Smith2024}", formatted)

    def test_convert_real_docx(self):
        docx_file = "Dissertation Chapter 4 (v1).docx"
        with tempfile.TemporaryDirectory() as tmpdir:
            if not os.path.isfile(docx_file):
                docx_file = os.path.join(tmpdir, "ch4_fixture.docx")
                create_sample_docx(docx_file)

            converter = DocxConverter()
            out_tex = os.path.join(tmpdir, "ch4_test.tex")
            latex_out = converter.convert(
                docx_path=docx_file,
                output_tex=out_tex,
                as_chapter=True,
                chapter_title="Conclusions and Future Directions",
                chapter_label="ch:conclusions_test",
            )

            self.assertTrue(os.path.isfile(out_tex))
            self.assertIn(r"\chapter{Conclusions and Future Directions}", latex_out)
            self.assertIn(r"\label{ch:conclusions_test}", latex_out)
            self.assertGreater(len(latex_out), 500)


if __name__ == "__main__":
    unittest.main()
