"""
pipeline.cli
============
Command-line interface for the Dissertation Template & Agentic Pipeline.
Supports reference extraction, docx conversion, LaTeX compilation, and rubric validation.
"""

import sys
import os
import argparse
import json
from typing import List, Optional

from .reference_extractor import ReferenceExtractor, extract_docx_references
from .docx_converter import DocxConverter, convert_docx_to_latex
from .rubric_validator import RubricValidator, RubricReport
from .compiler import LatexCompiler, compile_dissertation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipeline",
        description="Dissertation Template & Agentic Pipeline (UCSF Rubric Compliant)",
        epilog="Example: python3 run_pipeline.py validate-rubric"
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available pipeline subcommands")

    # 1. extract-refs
    p_extract = subparsers.add_parser("extract-refs", help="Extract references and DOIs from Word (.docx) manuscript")
    p_extract.add_argument("docx_file", help="Input .docx Word manuscript")
    p_extract.add_argument("-o", "--output-bib", default="references.bib", help="Output BibTeX file (default: references.bib)")
    p_extract.add_argument("-d", "--dois", default="doi_list.txt", help="Output DOI list file (default: doi_list.txt)")
    p_extract.add_argument("-m", "--map", default="citation_map.json", help="Output citation mapping JSON file")
    p_extract.add_argument("-l", "--local-bib", nargs="*", default=["dissertation_references.bib"],
                           help="Existing .bib files for offline / local metadata cache lookup")
    p_extract.add_argument("-e", "--email", help="Polite User-Agent email for Crossref/PubMed")
    p_extract.add_argument("-v", "--verbose", action="store_true", help="Verbose console output")

    # 2. convert-docx
    p_convert = subparsers.add_parser("convert-docx", help="Convert Word (.docx) manuscript to rubric-compliant LaTeX")
    p_convert.add_argument("docx_file", help="Input .docx Word manuscript")
    p_convert.add_argument("-o", "--output-tex", required=True, help="Output .tex chapter file")
    p_convert.add_argument("-m", "--map", help="Citation mapping JSON from extract-refs")
    p_convert.add_argument("-t", "--title", help="Explicit Chapter title")
    p_convert.add_argument("--label", help="LaTeX chapter label (e.g. ch:conclusions)")

    # 3. validate-rubric
    p_validate = subparsers.add_parser("validate-rubric", help="Audit dissertation project against UCSF Dissertation Rubric")
    p_validate.add_argument("-t", "--tex", default="dissertation_master.tex", help="Master LaTeX document (default: dissertation_master.tex)")
    p_validate.add_argument("--log", help="Compilation .log file path (default: <master>.log)")
    p_validate.add_argument("-j", "--json", help="Optional path to save JSON validation audit report")

    # 4. build
    p_build = subparsers.add_parser("build", help="Compile dissertation via latexmk/pdflatex + biber")
    p_build.add_argument("-t", "--tex", default="dissertation_master.tex", help="Master LaTeX document to compile")
    p_build.add_argument("--validate", action="store_true", help="Automatically run rubric validation audit after build")

    # 5. full-pipeline
    p_full = subparsers.add_parser("full-pipeline", help="Run full pipeline: extract -> convert -> build -> validate")
    p_full.add_argument("--docx", help="Optional DOCX file to extract and convert before building")
    p_full.add_argument("-t", "--tex", default="dissertation_master.tex", help="Master LaTeX document")
    p_full.add_argument("-o", "--output-tex", help="Output .tex chapter if converting docx")
    p_full.add_argument("-l", "--local-bib", nargs="*", default=["dissertation_references.bib"], help="Local bib files")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.subcommand:
        parser.print_help()
        return 0

    if args.subcommand == "extract-refs":
        print(f"\n[*] Running Reference Extractor on: {args.docx_file}")
        valid_local = [p for p in args.local_bib if os.path.isfile(p)] if args.local_bib else []
        if valid_local:
            print(f"[*] Loaded local BibTeX caches: {valid_local}")

        res = extract_docx_references(
            docx_file=args.docx_file,
            output_bib=args.output_bib,
            output_dois=args.dois,
            output_map=args.map,
            email=args.email,
            local_bib_paths=valid_local,
            verbose=args.verbose,
        )
        print(f"[✓] Extraction complete. Found {res['total_extracted']} references, {res['formal_dois']} DOIs.")
        print(f"    - BibTeX: {args.output_bib}")
        print(f"    - DOIs:   {args.dois}")
        if args.map:
            print(f"    - Map:    {args.map}")
        return 0

    elif args.subcommand == "convert-docx":
        print(f"\n[*] Converting DOCX to LaTeX: {args.docx_file} -> {args.output_tex}")
        cmap = {}
        if args.map and os.path.isfile(args.map):
            with open(args.map, 'r', encoding='utf-8') as f:
                cmap = json.load(f)
            print(f"[*] Loaded citation map with {len(cmap)} entries.")

        convert_docx_to_latex(
            docx_path=args.docx_file,
            output_tex=args.output_tex,
            citation_map=cmap,
            chapter_title=args.title,
            chapter_label=args.label,
        )
        print(f"[✓] Conversion complete: {args.output_tex}")
        return 0

    elif args.subcommand == "validate-rubric":
        tex_path = args.tex
        if not os.path.isfile(tex_path):
            candidate = "templates/latex/dissertation_master_template.tex"
            if os.path.isfile(candidate):
                print(f"[*] '{tex_path}' not found; falling back to template: {candidate}")
                tex_path = candidate
        print(f"\n[*] Auditing UCSF Dissertation Rubric Compliance: {tex_path}")
        validator = RubricValidator(master_tex_path=tex_path, log_path=args.log)
        report = validator.validate_all()
        report.print_summary()

        if args.json:
            with open(args.json, 'w', encoding='utf-8') as f:
                json.dump(report.to_dict(), f, indent=2)
            print(f"[*] Saved JSON audit report to {args.json}")

        return 0 if report.is_compliant else 1

    elif args.subcommand == "build":
        tex_path = args.tex
        if not os.path.isfile(tex_path):
            candidate = "templates/latex/dissertation_master_template.tex"
            if os.path.isfile(candidate):
                print(f"[*] '{tex_path}' not found; falling back to template: {candidate}")
                tex_path = candidate
        print(f"\n[*] Compiling Dissertation: {tex_path}")
        compiler = LatexCompiler(master_tex_path=tex_path)
        res = compiler.compile()

        if res.success:
            print(f"[✓] Build SUCCESS! Generated PDF ({res.page_count} pages): {res.output_pdf}")
        else:
            print(f"[!] Build FAILED (code {res.return_code}).")
            for err in res.errors:
                print(f"    Error: {err}")
            return 1

        if args.validate:
            print("\n[*] Running post-build rubric validation audit...")
            validator = RubricValidator(master_tex_path=tex_path)
            report = validator.validate_all()
            report.print_summary()
            return 0 if report.is_compliant else 1

        return 0

    elif args.subcommand == "full-pipeline":
        print("\n" + "=" * 70)
        print(" RUNNING FULL DISSERTATION AGENTIC PIPELINE")
        print("=" * 70)

        # Step 1: Optional DOCX Reference Extraction and Conversion
        cmap = {}
        if args.docx:
            print(f"\n--- [1/4] Extracting References from: {args.docx} ---")
            valid_local = [p for p in args.local_bib if os.path.isfile(p)] if args.local_bib else []
            res_ext = extract_docx_references(
                docx_file=args.docx,
                output_bib="extracted_references.bib",
                output_dois="extracted_dois.txt",
                output_map="citation_map.json",
                local_bib_paths=valid_local,
            )
            cmap = res_ext['citation_map']

            out_tex = args.output_tex or f"{os.path.splitext(args.docx)[0]}.tex"
            print(f"\n--- [2/4] Converting DOCX to LaTeX: {out_tex} ---")
            convert_docx_to_latex(
                docx_path=args.docx,
                output_tex=out_tex,
                citation_map=cmap,
            )

        # Step 2: Compile Dissertation
        tex_path = args.tex
        if not os.path.isfile(tex_path):
            candidate = "templates/latex/dissertation_master_template.tex"
            if os.path.isfile(candidate):
                print(f"[*] '{tex_path}' not found; falling back to template: {candidate}")
                tex_path = candidate
        print(f"\n--- [3/4] Compiling Master Dissertation: {tex_path} ---")
        compiler = LatexCompiler(master_tex_path=tex_path)
        comp_res = compiler.compile()

        if not comp_res.success:
            print(f"[!] Compilation failed.")
            return 1

        print(f"[✓] PDF Generated ({comp_res.page_count} pages): {comp_res.output_pdf}")

        # Step 3: Validate Rubric
        print(f"\n--- [4/4] Validating All Aspects of UCSF Rubric ---")
        validator = RubricValidator(master_tex_path=args.tex)
        report = validator.validate_all()
        report.print_summary()

        return 0 if report.is_compliant else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
