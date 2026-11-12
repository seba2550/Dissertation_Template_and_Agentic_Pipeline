"""
Integration tests for the full Dissertation Template & Agentic Pipeline.
"""

import unittest
import os
import tempfile
import json
import shutil
from pipeline.cli import main
from pipeline.compiler import compile_dissertation
from pipeline.rubric_validator import RubricValidator
from tests.test_helpers import create_sample_docx


class TestPipelineIntegration(unittest.TestCase):

    def test_cli_extract_refs_command(self):
        """Tests run_pipeline.py extract-refs via CLI on real docx or generated fixture."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docx_file = "dissertation_intro_scg_v1.docx"
            if not os.path.isfile(docx_file):
                docx_file = os.path.join(tmpdir, "sample.docx")
                create_sample_docx(docx_file)

            out_bib = os.path.join(tmpdir, "intro.bib")
            out_dois = os.path.join(tmpdir, "intro_dois.txt")
            out_map = os.path.join(tmpdir, "intro_map.json")

            local_bib = "dissertation_references.bib" if os.path.isfile("dissertation_references.bib") else "templates/latex/references.bib"
            cmd_args = [
                "extract-refs",
                docx_file,
                "-o", out_bib,
                "-d", out_dois,
                "-m", out_map,
            ]
            if os.path.isfile(local_bib):
                cmd_args.extend(["-l", local_bib])

            ret = main(cmd_args)
            self.assertEqual(ret, 0)
            self.assertTrue(os.path.isfile(out_bib))
            self.assertTrue(os.path.isfile(out_dois))
            self.assertTrue(os.path.isfile(out_map))

            with open(out_map, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.assertGreater(len(data), 0)

    def test_cli_validate_rubric_command(self):
        """Tests run_pipeline.py validate-rubric via CLI."""
        target_tex = "dissertation_master.tex"
        if not os.path.isfile(target_tex):
            target_tex = "templates/latex/dissertation_master_template.tex"
        if not os.path.isfile(target_tex):
            self.skipTest("Neither dissertation_master.tex nor template found")

        with tempfile.TemporaryDirectory() as tmpdir:
            json_report = os.path.join(tmpdir, "report.json")
            ret = main([
                "validate-rubric",
                "-t", target_tex,
                "-j", json_report,
            ])
            self.assertEqual(ret, 0)
            self.assertTrue(os.path.isfile(json_report))

            with open(json_report, 'r', encoding='utf-8') as f:
                rep_data = json.load(f)
            self.assertTrue(rep_data['is_compliant'])
            self.assertEqual(rep_data['failed'], 0)

    def test_full_pipeline_cli_invocation(self):
        """Tests run_pipeline.py full-pipeline end-to-end command."""
        target_tex = "dissertation_master.tex"
        if not os.path.isfile(target_tex):
            target_tex = "templates/latex/dissertation_master_template.tex"
        if not os.path.isfile(target_tex):
            self.skipTest(f"{target_tex} not present in workspace")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Build from a copy so the test never writes PDFs or LaTeX build files into the repo.
            build_dir = os.path.join(tmpdir, "build")
            shutil.copytree(
                os.path.dirname(os.path.abspath(target_tex)), build_dir,
                ignore=shutil.ignore_patterns(
                    "*.aux", "*.bbl", "*.bcf", "*.blg", "*.fdb_latexmk", "*.fls", "*.log",
                    "*.lof", "*.lot", "*.out", "*.run.xml", "*.toc", "*.synctex.gz"),
            )
            target_tex = os.path.join(build_dir, os.path.basename(target_tex))

            docx_file = "Dissertation Chapter 4 (v1).docx"
            if not os.path.isfile(docx_file):
                docx_file = os.path.join(tmpdir, "sample_ch.docx")
                create_sample_docx(docx_file)

            out_tex = os.path.join(tmpdir, "converted_ch.tex")
            ret = main([
                "full-pipeline",
                "--docx", docx_file,
                "-o", out_tex,
                "-t", target_tex,
                # Keep all extraction outputs out of the template directory.
                "-b", os.path.join(tmpdir, "references.bib"),
                "-d", os.path.join(tmpdir, "extracted_dois.txt"),
                "-m", os.path.join(tmpdir, "citation_map.json"),
            ])
            self.assertEqual(ret, 0)
    def test_convert_ch_cli_alias(self):
        """Tests that 'convert-ch' alias invokes docx conversion identically to 'convert-docx'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sample_docx = os.path.join(tmpdir, "sample.docx")
            create_sample_docx(sample_docx)
            out_tex = os.path.join(tmpdir, "ch_alias.tex")

            ret = main([
                "convert-ch",
                sample_docx,
                "-o", out_tex,
                "-t", "Sample Title",
            ])
            self.assertEqual(ret, 0)
            self.assertTrue(os.path.isfile(out_tex))
            with open(out_tex, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertIn(r"\chapter{Sample Title}", content)

    def test_multi_docx_extract_refs(self):
        """Tests extract-refs command on multiple docx files consolidating references."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ch1_docx = os.path.join(tmpdir, "ch1.docx")
            ch2_docx = os.path.join(tmpdir, "ch2.docx")
            create_sample_docx(ch1_docx)
            create_sample_docx(ch2_docx)

            out_bib = os.path.join(tmpdir, "merged.bib")
            out_dois = os.path.join(tmpdir, "merged_dois.txt")
            out_map = os.path.join(tmpdir, "merged_map.json")
            local_bib = "synthetic_test_run/local_cache.bib" if os.path.isfile("synthetic_test_run/local_cache.bib") else "dissertation_references.bib"

            ret = main([
                "extract-refs",
                ch1_docx, ch2_docx,
                "-o", out_bib,
                "-d", out_dois,
                "-m", out_map,
                "-l", local_bib,
            ])
            self.assertEqual(ret, 0)
            self.assertTrue(os.path.isfile(out_bib))
            self.assertTrue(os.path.isfile(out_dois))
            self.assertTrue(os.path.isfile(out_map))
            with open(out_map, 'r', encoding='utf-8') as f:
                cmap = json.load(f)
            self.assertIn("10.1038/nature12345", cmap)

    def test_synthetic_directory_artifacts(self):
        """Validates that synthetic_test_run contains valid generated artifacts and passes rubric."""
        syn_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "synthetic_test_run")
        master_tex = os.path.join(syn_dir, "synthetic_master.tex")
        if not os.path.isfile(master_tex):
            self.skipTest(f"{master_tex} not found")

        validator = RubricValidator(master_tex_path=master_tex)
        report = validator.validate_all()
        self.assertTrue(report.is_compliant)
        self.assertEqual(report.failed_count, 0)


if __name__ == "__main__":
    unittest.main()

