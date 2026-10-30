"""
Dissertation Template & Agentic Pipeline
=========================================
A robust, modular pipeline to extract references from Microsoft Word documents (.docx),
convert manuscripts to rubric-compliant LaTeX, compile dissertations, and programmatically
validate every aspect of institutional dissertation rubrics (specifically UCSF Dissertation Rubric).

Author: Computational Biology & Informatics Workflow
"""

from .reference_extractor import ReferenceExtractor, extract_docx_references
from .docx_converter import DocxConverter, convert_docx_to_latex
from .rubric_validator import RubricValidator, RubricReport
from .compiler import LatexCompiler, compile_dissertation

__version__ = "1.0.0"

__all__ = [
    "ReferenceExtractor",
    "extract_docx_references",
    "DocxConverter",
    "convert_docx_to_latex",
    "RubricValidator",
    "RubricReport",
    "LatexCompiler",
    "compile_dissertation",
]
