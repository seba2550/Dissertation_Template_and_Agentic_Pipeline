"""
Unit tests for pipeline.reference_extractor and utils.
"""

import unittest
import os
import tempfile
import json
import subprocess
from pipeline.utils import (
    clean_doi,
    clean_pmid,
    clean_pmcid,
    parse_bibtex_file,
    to_sentence_case,
    sanitize_latex_text,
)
from pipeline.reference_extractor import ReferenceExtractor, extract_docx_references
from tests.test_helpers import create_sample_docx


class TestUtils(unittest.TestCase):

    def test_clean_doi(self):
        self.assertEqual(clean_doi("https://doi.org/10.1038/s41588-023-01501-z"), "10.1038/s41588-023-01501-z")
        self.assertEqual(clean_doi("http://dx.doi.org/10.1002/gepi.22083."), "10.1002/gepi.22083")
        self.assertEqual(clean_doi("doi: 10.1186/gb-2013-14-10-r115;"), "10.1186/gb-2013-14-10-r115")
        self.assertEqual(clean_doi("10.1016/j.cell.2020.01.001)"), "10.1016/j.cell.2020.01.001")
        self.assertEqual(clean_doi("(10.1038/s41588-023-01501-z)"), "10.1038/s41588-023-01501-z")
        self.assertEqual(clean_doi("10.1002/(SICI)1097-0142"), "10.1002/(SICI)1097-0142")
        self.assertEqual(clean_doi(""), "")

    def test_clean_pmid(self):
        self.assertEqual(clean_pmid("38196633"), "38196633")
        self.assertEqual(clean_pmid("PMID: 27668383"), "27668383")
        self.assertEqual(clean_pmid(""), "")

    def test_clean_pmcid(self):
        self.assertEqual(clean_pmcid("PMC8086086"), "PMC8086086")
        self.assertEqual(clean_pmcid("pmc12345"), "PMC12345")
        self.assertEqual(clean_pmcid(""), "")

    def test_to_sentence_case(self):
        self.assertEqual(to_sentence_case("METHODS AND PROCEDURES"), "Methods and procedures")
        self.assertEqual(to_sentence_case("DNA METHYLATION CLOCKS AND meQTL"), "DNA methylation clocks and meQTL")

    def test_sanitize_latex_text(self):
        self.assertEqual(sanitize_latex_text("50% of people & mice"), r"50\% of people \& mice")
        self.assertEqual(sanitize_latex_text("Gene #1_v2"), r"Gene \#1\_v2")


class TestReferenceExtractor(unittest.TestCase):

    def setUp(self):
        self.extractor = ReferenceExtractor()

    def test_resolve_url_to_identifier(self):
        # Direct DOI URL
        res = self.extractor.resolve_url_to_identifier("https://doi.org/10.1038/s41588-023-01501-z")
        self.assertEqual(res['type'], 'doi')
        self.assertEqual(res['id'], '10.1038/s41588-023-01501-z')

        # Nature URL
        res = self.extractor.resolve_url_to_identifier("https://www.nature.com/articles/s41576-024-00760-8")
        self.assertEqual(res['type'], 'doi')
        self.assertEqual(res['id'], '10.1038/s41576-024-00760-8')

        # BioRxiv URL
        res = self.extractor.resolve_url_to_identifier("https://www.biorxiv.org/content/10.1101/2023.01.01.123456v1")
        self.assertEqual(res['type'], 'doi')
        self.assertEqual(res['id'], '10.1101/2023.01.01.123456')

        # PubMed URL
        res = self.extractor.resolve_url_to_identifier("https://pubmed.ncbi.nlm.nih.gov/38196633/")
        self.assertEqual(res['type'], 'pmid')
        self.assertEqual(res['id'], '38196633')

        # PMC URL
        res = self.extractor.resolve_url_to_identifier("https://pmc.ncbi.nlm.nih.gov/articles/PMC8086086/")
        self.assertEqual(res['type'], 'pmcid')
        self.assertEqual(res['id'], 'PMC8086086')

        # arXiv URL
        res = self.extractor.resolve_url_to_identifier("https://arxiv.org/abs/2301.12345")
        self.assertEqual(res['type'], 'arxiv')
        self.assertEqual(res['id'], '2301.12345')

        # ScienceDirect PII
        res = self.extractor.resolve_url_to_identifier("https://www.sciencedirect.com/science/article/pii/S0959437X16301794")
        self.assertEqual(res['type'], 'pii')
        self.assertEqual(res['id'], 'S0959437X16301794')

        # Generic URL
        res = self.extractor.resolve_url_to_identifier("https://www.ucsf.edu/about")
        self.assertEqual(res['type'], 'url')

    def test_local_bib_cache_lookup(self):
        dummy_bib = """
@article{Smith2024,
  author = {Smith, John and Doe, Jane},
  title = {Epigenetics of Aging},
  journal = {Nature Aging},
  year = {2024},
  doi = {10.1038/s43587-024-00001-x}
}
"""
        with tempfile.NamedTemporaryFile('w', suffix='.bib', delete=False) as f:
            f.write(dummy_bib)
            temp_bib_path = f.name

        try:
            cached_extractor = ReferenceExtractor(local_bib_paths=[temp_bib_path])
            bib_res = cached_extractor.fetch_bibtex_from_doi("10.1038/s43587-024-00001-x")
            self.assertIsNotNone(bib_res)
            self.assertIn("Smith2024", bib_res)
            self.assertIn("Epigenetics of Aging", bib_res)
        finally:
            os.remove(temp_bib_path)

    def test_fallback_bibtex_creation_and_deduplication(self):
        existing = set()
        key1, bib1 = self.extractor.create_fallback_bibtex(
            "https://www.example.com/very/long/path/with/same/prefix/item1",
            existing_keys=existing
        )
        key2, bib2 = self.extractor.create_fallback_bibtex(
            "https://www.example.com/very/long/path/with/same/prefix/item2",
            existing_keys=existing
        )
        self.assertNotEqual(key1, key2)
        self.assertTrue(key1.startswith("ref_"))
        self.assertTrue(key2.startswith("ref_"))
        self.assertIn("@misc{", bib1)
        self.assertIn("@misc{", bib2)

    def test_process_fixture_docx(self):
        """Tests processing a generated fixture DOCX without requiring private manuscripts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sample_docx = os.path.join(tmpdir, "sample.docx")
            create_sample_docx(sample_docx)

            out_bib = os.path.join(tmpdir, "out.bib")
            out_dois = os.path.join(tmpdir, "dois.txt")
            out_map = os.path.join(tmpdir, "map.json")

            summary = self.extractor.process(
                docx_file=sample_docx,
                output_bib=out_bib,
                output_dois=out_dois,
                output_map=out_map,
            )

            self.assertTrue(os.path.isfile(out_bib))
            self.assertTrue(os.path.isfile(out_dois))
            self.assertTrue(os.path.isfile(out_map))
            self.assertGreater(summary['total_extracted'], 0)
            self.assertGreater(summary['formal_dois'], 0)
            self.assertIn('rId1', summary['citation_map'])

    def test_process_real_docx(self):
        docx_file = "dissertation_intro_scg_v1.docx"
        with tempfile.TemporaryDirectory() as tmpdir:
            if not os.path.isfile(docx_file):
                docx_file = os.path.join(tmpdir, "intro_fixture.docx")
                create_sample_docx(docx_file)

            out_bib = os.path.join(tmpdir, "out.bib")
            out_dois = os.path.join(tmpdir, "dois.txt")
            out_map = os.path.join(tmpdir, "map.json")

            summary = self.extractor.process(
                docx_file=docx_file,
                output_bib=out_bib,
                output_dois=out_dois,
                output_map=out_map,
            )

            self.assertTrue(os.path.isfile(out_bib))
            self.assertTrue(os.path.isfile(out_dois))
            self.assertTrue(os.path.isfile(out_map))
            self.assertGreater(summary['total_extracted'], 0)
            self.assertGreater(summary['formal_dois'], 0)

    def test_resolve_extended_publisher_urls(self):
        # Aging (Albany NY)
        res = self.extractor.resolve_url_to_identifier("https://www.aging-us.com/article/100809/text")
        self.assertEqual(res['type'], 'doi')
        self.assertEqual(res['id'], '10.18632/aging.100809')

        # eLife
        res = self.extractor.resolve_url_to_identifier("https://elifesciences.org/articles/73420")
        self.assertEqual(res['type'], 'doi')
        self.assertEqual(res['id'], '10.7554/eLife.73420')

        # Genes & Development
        res = self.extractor.resolve_url_to_identifier("https://genesdev.cshlp.org/content/6/5/705.long")
        self.assertEqual(res['type'], 'doi')
        self.assertEqual(res['id'], '10.1101/gad.6.5.705')

        # Annual Reviews
        res = self.extractor.resolve_url_to_identifier("https://www.annualreviews.org/docserver/fulltext/biodatasci/5/1/annurev-biodatasci-111721-074830.pdf")
        self.assertEqual(res['type'], 'doi')
        self.assertEqual(res['id'], '10.1146/annurev-biodatasci-111721-074830')

    def test_pmcid_caching_and_resolution(self):
        dummy_bib = """
@article{PMCAuthor2023,
  author = {Doe, John},
  title = {A PMC Study},
  journal = {PMC Journal},
  year = {2023},
  note = {PMCID: PMC8086086},
  doi = {10.1000/pmc.8086086}
}
"""
        with tempfile.NamedTemporaryFile('w', suffix='.bib', delete=False) as f:
            f.write(dummy_bib)
            temp_bib_path = f.name

        try:
            cached_extractor = ReferenceExtractor(local_bib_paths=[temp_bib_path])
            bib_res, doi = cached_extractor.fetch_metadata_from_pmcid("PMC8086086")
            self.assertIsNotNone(bib_res)
            self.assertIn("PMCAuthor2023", bib_res)
            self.assertEqual(doi, "10.1000/pmc.8086086")
        finally:
            os.remove(temp_bib_path)

    def test_standalone_script_execution(self):
        script_candidates = [
            "agentic_scripts/extract_docx_references.py",
            "docx_reference_extractor/extract_docx_references.py",
        ]
        chosen_script = None
        for s in script_candidates:
            if os.path.isfile(s):
                chosen_script = s
                break

        if not chosen_script:
            self.skipTest("No standalone reference extraction script found")

        with tempfile.TemporaryDirectory() as tmpdir:
            sample_docx = os.path.join(tmpdir, "sample.docx")
            create_sample_docx(sample_docx)

            out_bib = os.path.join(tmpdir, "test.bib")
            out_dois = os.path.join(tmpdir, "test.dois")
            out_map = os.path.join(tmpdir, "test.map")

            cmd = [
                "python3",
                chosen_script,
                sample_docx,
                "-o", out_bib,
                "-d", out_dois,
                "-m", out_map,
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertEqual(res.returncode, 0, f"Error: {res.stderr}")
            self.assertTrue(os.path.isfile(out_bib))
            self.assertTrue(os.path.isfile(out_dois))
            self.assertTrue(os.path.isfile(out_map))


if __name__ == "__main__":
    unittest.main()
