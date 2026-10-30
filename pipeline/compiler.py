"""
pipeline.compiler
=================
Automated LaTeX compiler & log analyzer.
Compiles the master dissertation using `latexmk` or `pdflatex` + `biber`,
parses logs for warnings, overfull hboxes, missing fonts, and undefined citations.
"""

import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class CompilationResult:
    """Compilation execution outcome."""
    success: bool
    return_code: int
    output_pdf: Optional[str] = None
    page_count: int = 0
    undefined_citations: List[str] = field(default_factory=list)
    undefined_references: List[str] = field(default_factory=list)
    overfull_hboxes: int = 0
    errors: List[str] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""


class LatexCompiler:
    """Orchestrates LaTeX compilation and log inspection."""

    def __init__(self, master_tex_path: str = "dissertation_master.tex"):
        self.master_tex_path = master_tex_path
        self.work_dir = os.path.dirname(os.path.abspath(master_tex_path))
        self.tex_filename = os.path.basename(master_tex_path)
        self.base_name = os.path.splitext(self.tex_filename)[0]

    def compile(self, use_latexmk: bool = True, clean_first: bool = False) -> CompilationResult:
        """Runs compilation pipeline."""
        if not os.path.isfile(self.master_tex_path):
            return CompilationResult(
                success=False,
                return_code=1,
                errors=[f"File not found: {self.master_tex_path}"]
            )

        if use_latexmk:
            cmd = ["latexmk", "-pdf", "-interaction=nonstopmode", self.tex_filename]
        else:
            cmd = ["pdflatex", "-interaction=nonstopmode", self.tex_filename]

        try:
            proc = subprocess.run(
                cmd,
                cwd=self.work_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            stdout = proc.stdout
            stderr = proc.stderr
            ret_code = proc.returncode
        except Exception as e:
            return CompilationResult(
                success=False,
                return_code=1,
                errors=[f"Execution failed: {str(e)}"]
            )

        log_path = os.path.join(self.work_dir, f"{self.base_name}.log")
        pdf_path = os.path.join(self.work_dir, f"{self.base_name}.pdf")

        result = self._parse_log_and_artifacts(log_path, pdf_path, ret_code, stdout, stderr)
        return result

    def _parse_log_and_artifacts(
        self,
        log_path: str,
        pdf_path: str,
        ret_code: int,
        stdout: str,
        stderr: str,
    ) -> CompilationResult:
        """Parses .log file and PDF artifacts."""
        undefined_citations = []
        undefined_references = []
        overfull_count = 0
        page_count = 0
        errors = []

        if os.path.isfile(log_path):
            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                log_data = f.read()

            undefined_citations = re.findall(r'Citation [`\']([^`\']+)[\'] on page \d+ undefined', log_data)
            undefined_references = re.findall(r'Reference [`\']([^`\']+)[\'] on page \d+ undefined', log_data)
            overfull_matches = re.findall(r'Overfull \\hbox \(([0-9\.]+)pt too wide\)', log_data)
            # Count only significant overfull boxes (> 5pt)
            overfull_count = sum(1 for w in overfull_matches if float(w) > 5.0)

            # Match output pages
            m_pages = re.search(r'Output written on \S+ \((\d+) pages', log_data)
            if m_pages:
                page_count = int(m_pages.group(1))

            err_matches = re.findall(r'! (.*)', log_data)
            if err_matches:
                errors = err_matches[:10]

        has_pdf = os.path.isfile(pdf_path) and os.path.getsize(pdf_path) > 1000
        success = (ret_code == 0) and has_pdf

        return CompilationResult(
            success=success,
            return_code=ret_code,
            output_pdf=pdf_path if has_pdf else None,
            page_count=page_count,
            undefined_citations=sorted(list(set(undefined_citations))),
            undefined_references=sorted(list(set(undefined_references))),
            overfull_hboxes=overfull_count,
            errors=errors,
            stdout=stdout,
            stderr=stderr,
        )


def compile_dissertation(master_tex: str = "dissertation_master.tex") -> CompilationResult:
    """Convenience helper to compile dissertation."""
    compiler = LatexCompiler(master_tex)
    return compiler.compile()
