"""
pipeline.cli
============
Command-line interface for the Dissertation Template & Agentic Pipeline.
Supports reference extraction, docx conversion, LaTeX compilation, and rubric validation.
"""

import sys
import os
import re
import argparse
import json
from typing import List, Optional

from .reference_extractor import ReferenceExtractor, extract_docx_references
from .docx_converter import DocxConverter, convert_docx_to_latex
from .rubric_validator import RubricValidator, RubricReport
from .compiler import LatexCompiler, compile_dissertation


_BIB_ENTRY_START = re.compile(r'@\w+\s*\{\s*([^,\s]+)\s*,')


def _split_bib_entries(text: str) -> List[tuple]:
    """Returns [(key, raw_entry)] for each entry in a BibTeX string."""
    starts = list(_BIB_ENTRY_START.finditer(text))
    return [(m.group(1), text[m.start():(starts[i + 1].start() if i + 1 < len(starts) else len(text))].strip())
            for i, m in enumerate(starts)]


def _merge_bib_entries(src_bib: str, dest_bib: str) -> int:
    """Appends entries from src_bib whose keys are not already in dest_bib. Returns count added."""
    with open(dest_bib, 'r', encoding='utf-8', errors='ignore') as f:
        dest_text = f.read()
    with open(src_bib, 'r', encoding='utf-8', errors='ignore') as f:
        src_entries = _split_bib_entries(f.read())
    existing = {k.lower() for k, _ in _split_bib_entries(dest_text)}
    new = [raw for k, raw in src_entries if k.lower() not in existing]
    if new:
        with open(dest_bib, 'a', encoding='utf-8') as f:
            f.write(("\n" if dest_text and not dest_text.endswith("\n") else "") + "\n" + "\n\n".join(new) + "\n")
    return len(new)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipeline",
        description="Dissertation Template & Agentic Pipeline (UCSF Rubric Compliant)",
        epilog="Example: python3 run_pipeline.py validate-rubric"
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available pipeline subcommands")

    # 1. extract-refs
    p_extract = subparsers.add_parser("extract-refs", help="Extract references and DOIs from Word (.docx) manuscript(s)")
    p_extract.add_argument("docx_file", nargs="+", help="Input .docx Word manuscript(s)")
    p_extract.add_argument("-o", "--output-bib", default="references.bib", help="Output BibTeX file (default: references.bib)")
    p_extract.add_argument("-d", "--dois", default="doi_list.txt", help="Output DOI list file (default: doi_list.txt)")
    p_extract.add_argument("-m", "--map", default="citation_map.json", help="Output citation mapping JSON file")
    p_extract.add_argument("-l", "--local-bib", nargs="*", default=["dissertation_references.bib"],
                           help="Existing .bib files for offline / local metadata cache lookup")
    p_extract.add_argument("-e", "--email", help="Polite User-Agent email for Crossref/PubMed")
    p_extract.add_argument("-v", "--verbose", action="store_true", help="Verbose console output")

    # 2. convert-docx
    p_convert = subparsers.add_parser("convert-docx", aliases=["convert-ch"], help="Convert Word (.docx) manuscript(s) to rubric-compliant LaTeX")
    p_convert.add_argument("docx_file", nargs="+", help="Input .docx Word manuscript(s)")
    p_convert.add_argument("-o", "--output-tex", nargs="*", help="Output .tex chapter file(s)")
    p_convert.add_argument("-m", "--map", help="Citation mapping JSON from extract-refs")
    p_convert.add_argument("-t", "--title", help="Explicit Chapter title (single document only)")
    p_convert.add_argument("--label", help="LaTeX chapter label (single document only)")

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
    p_full.add_argument("--docx", nargs="*", help="Optional DOCX file(s) to extract and convert before building")
    p_full.add_argument("-t", "--tex", default="dissertation_master.tex", help="Master LaTeX document")
    p_full.add_argument("-o", "--output-tex", nargs="*", help="Output .tex chapter(s) if converting docx")
    p_full.add_argument("-b", "--output-bib", help="Output BibTeX file (defaults to bib resource in master tex)")
    p_full.add_argument("-d", "--dois", help="Output DOI list file (default: extracted_dois.txt)")
    p_full.add_argument("-m", "--map", help="Citation mapping JSON file (default: citation_map.json)")
    p_full.add_argument("-l", "--local-bib", nargs="*", default=["dissertation_references.bib"], help="Local bib files")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.subcommand:
        parser.print_help()
        return 0

    if args.subcommand == "extract-refs":
        doc_list = args.docx_file if isinstance(args.docx_file, list) else [args.docx_file]
        desc = doc_list[0] if len(doc_list) == 1 else f"{len(doc_list)} manuscripts: {doc_list}"
        print(f"\n[*] Running Reference Extractor on: {desc}")
        valid_local = [p for p in args.local_bib if os.path.isfile(p)] if args.local_bib else []
        if valid_local:
            print(f"[*] Loaded local BibTeX caches: {valid_local}")

        res = extract_docx_references(
            docx_file=doc_list if len(doc_list) > 1 else doc_list[0],
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

    elif args.subcommand in ("convert-docx", "convert-ch"):
        doc_list = args.docx_file if isinstance(args.docx_file, list) else [args.docx_file]
        outputs = args.output_tex if isinstance(args.output_tex, list) else ([args.output_tex] if args.output_tex else [])

        cmap = {}
        if args.map and os.path.isfile(args.map):
            with open(args.map, 'r', encoding='utf-8') as f:
                cmap = json.load(f)
            print(f"[*] Loaded citation map with {len(cmap)} entries.")

        for i, docx_p in enumerate(doc_list):
            out_t = outputs[i] if i < len(outputs) else f"{os.path.splitext(docx_p)[0]}.tex"
            ch_title = args.title if len(doc_list) == 1 else None
            ch_label = args.label if len(doc_list) == 1 else None
            print(f"\n[*] Converting DOCX to LaTeX: {docx_p} -> {out_t}")
            convert_docx_to_latex(
                docx_path=docx_p,
                output_tex=out_t,
                citation_map=cmap,
                chapter_title=ch_title,
                chapter_label=ch_label,
            )
            print(f"[✓] Conversion complete: {out_t}")
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

        tex_path = args.tex
        if not os.path.isfile(tex_path):
            candidate = "templates/latex/dissertation_master_template.tex"
            if os.path.isfile(candidate):
                print(f"[*] '{tex_path}' not found; falling back to template: {candidate}")
                tex_path = candidate

        # Determine output bib location intelligently
        out_bib = args.output_bib
        if not out_bib:
            if os.path.isfile(tex_path):
                with open(tex_path, 'r', encoding='utf-8', errors='ignore') as f:
                    m_bib = re.search(r'\\addbibresource\{([^}]+)\}', f.read())
                    if m_bib:
                        bib_filename = m_bib.group(1).strip()
                        out_bib = os.path.normpath(os.path.join(os.path.dirname(tex_path) or ".", bib_filename))
            if not out_bib:
                out_bib = os.path.join(os.path.dirname(tex_path) or ".", "references.bib")

        out_dois = args.dois or os.path.join(os.path.dirname(out_bib) or ".", "extracted_dois.txt")
        out_map = args.map or os.path.join(os.path.dirname(out_bib) or ".", "citation_map.json")

        # Step 1: Optional DOCX Reference Extraction and Conversion
        cmap = {}
        if args.docx:
            doc_list = args.docx if isinstance(args.docx, list) else [args.docx]
            print(f"\n--- [1/4] Extracting References from {len(doc_list)} manuscript(s): {doc_list} ---")
            valid_local = [p for p in args.local_bib if os.path.isfile(p)] if args.local_bib else []
            if valid_local:
                print(f"[*] Loaded local BibTeX caches: {valid_local}")

            # Never clobber an existing bibliography the user didn't explicitly name with -b:
            # extract to a sibling file, then append only entries whose keys are new.
            merge_into = out_bib if (not args.output_bib and os.path.isfile(out_bib)) else None
            extract_target = (os.path.splitext(out_bib)[0] + ".extracted.bib") if merge_into else out_bib
            res_ext = extract_docx_references(
                docx_file=doc_list if len(doc_list) > 1 else doc_list[0],
                output_bib=extract_target,
                output_dois=out_dois,
                output_map=out_map,
                local_bib_paths=valid_local,
            )
            cmap = res_ext['citation_map']
            if merge_into:
                added = _merge_bib_entries(extract_target, merge_into)
                os.remove(extract_target)
                print(f"[*] Merged {added} new entries into existing {merge_into} (existing entries preserved).")
            print(f"[✓] Extraction complete. Found {res_ext['total_extracted']} references, {res_ext['formal_dois']} DOIs.")
            print(f"    - BibTeX: {out_bib}")
            print(f"    - DOIs:   {out_dois}")
            print(f"    - Map:    {out_map}")

            outputs = args.output_tex if isinstance(args.output_tex, list) else ([args.output_tex] if args.output_tex else [])
            print(f"\n--- [2/4] Converting {len(doc_list)} DOCX manuscript(s) to LaTeX ---")
            for i, docx_p in enumerate(doc_list):
                out_t = outputs[i] if i < len(outputs) else f"{os.path.splitext(docx_p)[0]}.tex"
                print(f"[*] Converting: {docx_p} -> {out_t}")
                convert_docx_to_latex(
                    docx_path=docx_p,
                    output_tex=out_t,
                    citation_map=cmap,
                )
                print(f"[✓] Converted: {out_t}")

        # Step 2: Compile Dissertation
        print(f"\n--- [3/4] Compiling Master Dissertation: {tex_path} ---")
        compiler = LatexCompiler(master_tex_path=tex_path)
        comp_res = compiler.compile()

        if not comp_res.success:
            print(f"[!] Compilation failed (code {comp_res.return_code}).")
            for err in comp_res.errors:
                print(f"    Error: {err}")
            return 1

        print(f"[✓] PDF Generated ({comp_res.page_count} pages): {comp_res.output_pdf}")

        # Step 3: Validate Rubric
        print(f"\n--- [4/4] Validating All Aspects of UCSF Rubric ---")
        validator = RubricValidator(master_tex_path=tex_path)
        report = validator.validate_all()
        report.print_summary()

        return 0 if report.is_compliant else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
