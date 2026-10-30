#!/usr/bin/env python3
"""
run_pipeline.py
===============
Top-level entrypoint for the Dissertation Template & Agentic Pipeline.
Executes reference extraction, docx conversion, compilation, and rubric validation.

Usage examples:
  python3 run_pipeline.py validate-rubric
  python3 run_pipeline.py build --validate
  python3 run_pipeline.py extract-refs "dissertation_intro_scg_v1.docx" -o intro_refs.bib
  python3 run_pipeline.py full-pipeline
"""

import sys
from pipeline.cli import main

if __name__ == "__main__":
    sys.exit(main())
