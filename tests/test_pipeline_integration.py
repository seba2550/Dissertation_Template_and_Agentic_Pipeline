"""
Integration tests for the full Dissertation Template & Agentic Pipeline.
"""

import unittest
import os
import tempfile
import json
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

            local_bib = "dissertation_references.bib" if os.path.isfile("dissertation_references.bib") else "templates/latex/references_template.bib"
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
            ])
            self.assertEqual(ret, 0)
            self.assertTrue(os.path.isfile(out_tex))


if __name__ == "__main__":
    unittest.main()
