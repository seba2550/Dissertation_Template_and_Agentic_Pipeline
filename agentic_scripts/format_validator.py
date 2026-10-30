#!/usr/bin/env python3
"""
format_validator.py
===================
Institutional Dissertation Rubric Verification Script.
Executes an exhaustive 26-rule programmatic audit against the master LaTeX
dissertation source, preamble configuration, structural components, bib resources,
and compilation log artifacts (UCSF Dissertation Rubric Rev 04/24).

Usage:
  python3 agentic_scripts/format_validator.py
  python3 agentic_scripts/format_validator.py templates/latex/dissertation_master_template.tex
  python3 agentic_scripts/format_validator.py dissertation_master.tex --json audit_report.json
"""

import sys
import os
import argparse
import json

# Ensure repository root is on sys.path
_script_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(_script_dir)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from pipeline.rubric_validator import RubricValidator, RubricReport


def main():
    parser = argparse.ArgumentParser(
        description="Comprehensive 26-Rule Institutional Dissertation Rubric Validator"
    )
    parser.add_argument(
        "tex_file",
        nargs="?",
        default="dissertation_master.tex",
        help="Path to master LaTeX document (default: dissertation_master.tex)",
    )
    parser.add_argument(
        "--log",
        help="Path to LaTeX compilation log file (default: <master>.log)",
    )
    parser.add_argument(
        "-j",
        "--json",
        help="Optional output path to export JSON audit report",
    )
    args = parser.parse_args()

    # Fallback to template if default not present
    tex_path = args.tex_file
    if not os.path.isfile(tex_path):
        candidate_template = os.path.join(_repo_root, "templates", "latex", "dissertation_master_template.tex")
        if os.path.isfile(candidate_template):
            print(f"[*] Default '{tex_path}' not found; auditing template: {candidate_template}")
            tex_path = candidate_template

    print(f"\n[*] Auditing UCSF Dissertation Rubric Compliance: {tex_path}")
    validator = RubricValidator(master_tex_path=tex_path, log_path=args.log)
    report = validator.validate_all()
    report.print_summary()

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2)
        print(f"[*] Saved JSON audit report to {args.json}")

    return 0 if report.is_compliant else 1


if __name__ == "__main__":
    sys.exit(main())
