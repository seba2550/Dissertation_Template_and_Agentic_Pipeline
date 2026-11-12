"""
Regression tests for code-review fixes:
1. full-pipeline must not overwrite an existing bibliography it was not explicitly told to write.
2. DOIs inside URLs must be converted as whole URLs, not leave URL fragments around a \\cite.
3. Hyperlink relationship IDs (rIdN) must be scoped per document in multi-document runs.
4. The dead _extract_paragraphs helper stays removed.
"""

import json
import os
import tempfile
import unittest
from unittest import mock

from pipeline.cli import main, _merge_bib_entries
from pipeline.docx_converter import DocxConverter
from pipeline.reference_extractor import ReferenceExtractor
from tests.test_helpers import create_sample_docx

LOCAL_CACHE = "synthetic_test_run/local_cache.bib"

HAND_ENTRY = """@article{HandCurated2020,
  title = {A Hand-Curated Reference},
  author = {Doe, Jane},
  year = {2020}
}
"""


class TestFullPipelinePreservesBibliography(unittest.TestCase):

    def _run_full_pipeline(self, tmpdir, extra_args=()):
        master = os.path.join(tmpdir, "master.tex")
        with open(master, "w", encoding="utf-8") as f:
            f.write("\\documentclass{report}\n\\addbibresource{refs.bib}\n\\begin{document}\\end{document}\n")
        docx = os.path.join(tmpdir, "ch1.docx")
        create_sample_docx(docx)
        local = [LOCAL_CACHE] if os.path.isfile(LOCAL_CACHE) else []
        failed_build = mock.MagicMock(success=False, return_code=1, errors=[])
        with mock.patch("pipeline.cli.LatexCompiler") as compiler_cls:
            compiler_cls.return_value.compile.return_value = failed_build
            main(["full-pipeline", "--docx", docx,
                  "-o", os.path.join(tmpdir, "ch1.tex"),
                  "-t", master, "-l", *local, *extra_args])

    def test_existing_bib_is_preserved_and_extended(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bib = os.path.join(tmpdir, "refs.bib")
            with open(bib, "w", encoding="utf-8") as f:
                f.write(HAND_ENTRY)

            self._run_full_pipeline(tmpdir)

            with open(bib, encoding="utf-8") as f:
                content = f.read()
            self.assertTrue(content.startswith(HAND_ENTRY), "hand-curated entry was altered or removed")
            self.assertGreater(content.count("@"), 1, "extracted entries were not appended")
            self.assertFalse(os.path.exists(os.path.join(tmpdir, "refs.extracted.bib")),
                             "temporary extraction file was left behind")

    def test_explicit_output_bib_is_written_directly(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            explicit = os.path.join(tmpdir, "explicit.bib")
            with open(explicit, "w", encoding="utf-8") as f:
                f.write(HAND_ENTRY)

            self._run_full_pipeline(tmpdir, ["-b", explicit])

            with open(explicit, encoding="utf-8") as f:
                self.assertNotIn("HandCurated2020", f.read())

    def test_merge_skips_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = os.path.join(tmpdir, "dest.bib")
            src = os.path.join(tmpdir, "src.bib")
            with open(dest, "w", encoding="utf-8") as f:
                f.write(HAND_ENTRY)
            with open(src, "w", encoding="utf-8") as f:
                f.write("@article{handcurated2020,\n  title = {Replacement}\n}\n\n"
                        "@article{New2024,\n  title = {New}\n}\n")

            self.assertEqual(_merge_bib_entries(src, dest), 1)
            with open(dest, encoding="utf-8") as f:
                content = f.read()
            self.assertIn("A Hand-Curated Reference", content)
            self.assertNotIn("Replacement", content)
            self.assertIn("New2024", content)


class TestDoiInsideUrl(unittest.TestCase):

    def test_doi_url_becomes_single_cite(self):
        conv = DocxConverter({"10.1234/abc": "Key2020", "https://doi.org/10.1234/abc": "Key2020"})
        out = conv._format_text_with_inline_citations("See https://doi.org/10.1234/abc.")
        self.assertEqual(out, "See \\cite{Key2020}.")
        self.assertNotIn("doi.org", out)

    def test_bare_doi_still_converted(self):
        conv = DocxConverter({"10.1234/abc": "Key2020"})
        out = conv._format_text_with_inline_citations("As shown in 10.1234/abc, ...")
        self.assertIn("\\cite{Key2020}", out)


class TestRelationshipIdScoping(unittest.TestCase):

    def test_multi_doc_extraction_has_no_bare_rids(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ch1, ch2 = os.path.join(tmpdir, "ch1.docx"), os.path.join(tmpdir, "ch2.docx")
            create_sample_docx(ch1)
            create_sample_docx(ch2)
            local = [LOCAL_CACHE] if os.path.isfile(LOCAL_CACHE) else []
            summary = ReferenceExtractor(local_bib_paths=local).process(
                docx_file=[ch1, ch2],
                output_bib=os.path.join(tmpdir, "out.bib"),
                output_dois=os.path.join(tmpdir, "dois.txt"),
                output_map=os.path.join(tmpdir, "map.json"),
            )
            cmap = summary["citation_map"]
            self.assertIn("ch1.docx::rId1", cmap)
            self.assertIn("ch2.docx::rId1", cmap)
            self.assertNotIn("rId1", cmap)

    def test_converter_prefers_document_scoped_rid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ch2 = os.path.join(tmpdir, "ch2.docx")
            create_sample_docx(ch2)
            # Target DOIs deliberately absent so lookup falls through to the rId fallback.
            conv = DocxConverter({"rId1": "WrongChapterKey", "ch2.docx::rId1": "RightKey"})
            latex = conv.convert(docx_path=ch2, as_chapter=True, chapter_title="Ch2")
            self.assertIn("\\cite{RightKey}", latex)
            self.assertNotIn("WrongChapterKey", latex)


class TestDeadCodeRemoved(unittest.TestCase):

    def test_extract_paragraphs_removed(self):
        self.assertFalse(hasattr(DocxConverter, "_extract_paragraphs"))


if __name__ == "__main__":
    unittest.main()
