"""
pipeline.docx_converter
=======================
Converts Microsoft Word (.docx) documents into clean, rubric-compliant LaTeX chapters.
- Maps Word heading styles to UCSF Rubric hierarchy:
    * Document Title / Chapter -> \\chapter{...} or \\section{...}
    * Heading 1 -> \\section{...}
    * Heading 2 -> \\subsection{...}
    * Heading 3 -> \\subsubsection{...}
- Converts embedded hyperlinks and reference tags to \\cite{...} using citation maps.
- Enforces single-spaced block quotes for long quotations (>4 lines / 40 words).
- Zero external dependencies: uses Python's standard zipfile and xml.etree.ElementTree.
"""

import os
import re
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple, Any

from .utils import (
    to_sentence_case,
    sanitize_latex_text,
    clean_doi,
    W_NS,
    R_NS,
)


class DocxConverter:
    """
    Parses Word XML structure and converts paragraphs, headings, inline styles,
    and hyperlinks into rubric-compliant LaTeX source code.
    """

    def __init__(self, citation_map: Optional[Dict[str, str]] = None):
        """
        citation_map: Optional dictionary mapping URLs, DOIs, or raw citation strings to BibTeX keys.
        """
        self.citation_map = citation_map or {}

    def convert(
        self,
        docx_path: str,
        output_tex: Optional[str] = None,
        as_chapter: bool = True,
        chapter_title: Optional[str] = None,
        chapter_label: Optional[str] = None,
    ) -> str:
        """
        Converts a .docx document into LaTeX text.
        If output_tex is provided, writes output to file.
        """
        if not os.path.isfile(docx_path):
            raise FileNotFoundError(f"File not found: {docx_path}")

        paragraphs, rel_map = self._extract_paragraphs(docx_path)
        latex_lines: List[str] = []

        # If a chapter header is explicitly requested
        if as_chapter and chapter_title:
            latex_lines.append(f"\\chapter{{{chapter_title}}}")
            if chapter_label:
                latex_lines.append(f"\\label{{{chapter_label}}}")
            latex_lines.append("")
            first_heading_seen = True
        else:
            first_heading_seen = False

        for para in paragraphs:
            style = para.get('style', '').lower()
            text = para.get('text', '').strip()
            runs = para.get('runs', [])

            if not text:
                continue

            # Detect Markdown-style heading prefixes (# Heading, ## Heading, etc.)
            md_match = re.match(r'^(#{1,4})\s+(.+)$', text)

            is_h1 = bool(re.search(r'heading\s*1', style)) or (style == 'title') or (md_match and len(md_match.group(1)) == 1)
            is_h2 = bool(re.search(r'heading\s*2', style)) or (style == 'subtitle') or (md_match and len(md_match.group(1)) == 2)
            is_h3 = bool(re.search(r'heading\s*3', style)) or (md_match and len(md_match.group(1)) == 3)
            is_h4 = bool(re.search(r'heading\s*4', style)) or (md_match and len(md_match.group(1)) == 4)

            # Determine if paragraph is a heading
            if is_h1:
                raw_title = md_match.group(2) if md_match else text
                # If text starts with e.g. "Chapter 4: Title" or "Chapter IV: Title", strip prefix if formatting as chapter
                if as_chapter and not chapter_title and not first_heading_seen:
                    raw_title = re.sub(r'^[Cc]hapter\s+[0-9IVXLCDMivxlcdm]+[:\.\s\-]+\s*', '', raw_title).strip()
                cleaned_title = to_sentence_case(raw_title)
                if as_chapter and not chapter_title and not first_heading_seen:
                    first_heading_seen = True
                    latex_lines.append(f"\\chapter{{{cleaned_title}}}")
                    if chapter_label:
                        latex_lines.append(f"\\label{{{chapter_label}}}")
                    latex_lines.append("")
                else:
                    latex_lines.append(f"\\section{{{cleaned_title}}}")
                    latex_lines.append("")
            elif is_h2:
                raw_title = md_match.group(2) if md_match else text
                # Strip numeric subsection prefixes like "4.1 "
                raw_title = re.sub(r'^\d+\.\d+\s*', '', raw_title).strip()
                cleaned_title = to_sentence_case(raw_title)
                latex_lines.append(f"\\subsection{{{cleaned_title}}}")
                latex_lines.append("")
            elif is_h3 or is_h4:
                raw_title = md_match.group(2) if md_match else text
                raw_title = re.sub(r'^\d+\.\d+\.\d+\s*', '', raw_title).strip()
                cleaned_title = to_sentence_case(raw_title)
                latex_lines.append(f"\\subsubsection{{{cleaned_title}}}")
                latex_lines.append("")
            elif 'quote' in style or 'quotation' in style or (len(text.split()) > 40 and para.get('indented', False)):
                # Prose quote blockquote per UCSF rubric Sec I.F & III.C (single-spaced & indented)
                formatted_body = self._format_runs(runs, rel_map)
                latex_lines.append("\\begin{quotation}")
                latex_lines.append("\\begin{singlespace}")
                latex_lines.append(f"  {formatted_body}")
                latex_lines.append("\\end{singlespace}")
                latex_lines.append("\\end{quotation}")
                latex_lines.append("")
            else:
                formatted_body = self._format_runs(runs, rel_map)
                latex_lines.append(formatted_body)
                latex_lines.append("")

        full_latex = "\n".join(latex_lines).strip() + "\n"

        if output_tex:
            with open(output_tex, 'w', encoding='utf-8') as f:
                f.write(full_latex)

        return full_latex

    def _extract_paragraphs(self, docx_path: str) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
        """Extracts structured paragraph objects and relationship mapping."""
        rel_map: Dict[str, str] = {}
        paragraphs: List[Dict[str, Any]] = []

        with zipfile.ZipFile(docx_path, 'r') as docx_zip:
            # 1. Parse document relationships
            if 'word/_rels/document.xml.rels' in docx_zip.namelist():
                xml_data = docx_zip.read('word/_rels/document.xml.rels')
                root = ET.fromstring(xml_data)
                for elem in root.iter():
                    if elem.tag.endswith('Relationship'):
                        r_id = elem.attrib.get('Id', '')
                        target = elem.attrib.get('Target', '')
                        if r_id and target:
                            rel_map[r_id] = target

            # 2. Parse word/document.xml
            if 'word/document.xml' in docx_zip.namelist():
                xml_data = docx_zip.read('word/document.xml')
                root = ET.fromstring(xml_data)

                # Iterate through body children (paragraphs, tables)
                body = root.find(f'{{{W_NS}}}body')
                if body is not None:
                    for child in body:
                        if child.tag == f'{{{W_NS}}}p':
                            para_info = self._parse_paragraph_node(child)
                            paragraphs.append(para_info)

        return paragraphs, rel_map

    def _parse_paragraph_node(self, p_node: ET.Element) -> Dict[str, Any]:
        """Parses a <w:p> node to extract style, runs, and hyperlinks."""
        style = ""
        indented = False
        pPr = p_node.find(f'{{{W_NS}}}pPr')
        if pPr is not None:
            pStyle = pPr.find(f'{{{W_NS}}}pStyle')
            if pStyle is not None:
                style = pStyle.attrib.get(f'{{{W_NS}}}val', '')
            ind = pPr.find(f'{{{W_NS}}}ind')
            if ind is not None:
                left_ind = ind.attrib.get(f'{{{W_NS}}}left', '0')
                try:
                    if int(left_ind) > 300:
                        indented = True
                except (ValueError, TypeError):
                    pass

        runs: List[Dict[str, Any]] = []
        full_text_parts: List[str] = []

        for child in p_node:
            if child.tag == f'{{{W_NS}}}r':
                run_data = self._parse_run_node(child)
                runs.append(run_data)
                full_text_parts.append(run_data['text'])
            elif child.tag == f'{{{W_NS}}}hyperlink':
                r_id = child.attrib.get(f'{{{R_NS}}}id', '')
                for sub in child.findall(f'{{{W_NS}}}r'):
                    run_data = self._parse_run_node(sub)
                    run_data['r_id'] = r_id
                    runs.append(run_data)
                    full_text_parts.append(run_data['text'])

        return {
            'style': style,
            'indented': indented,
            'text': "".join(full_text_parts),
            'runs': runs,
        }

    def _parse_run_node(self, r_node: ET.Element) -> Dict[str, Any]:
        """Parses a <w:r> node for text and styling (bold, italic, etc.)."""
        bold = False
        italic = False
        rPr = r_node.find(f'{{{W_NS}}}rPr')
        if rPr is not None:
            if rPr.find(f'{{{W_NS}}}b') is not None:
                bold = True
            if rPr.find(f'{{{W_NS}}}i') is not None:
                italic = True

        text_parts = []
        for t in r_node.findall(f'{{{W_NS}}}t'):
            if t.text:
                text_parts.append(t.text)

        return {
            'text': "".join(text_parts),
            'bold': bold,
            'italic': italic,
            'r_id': None,
        }

    def _format_runs(self, runs: List[Dict[str, Any]], rel_map: Dict[str, str]) -> str:
        """Formats runs into LaTeX text, applying formatting and citation replacements."""
        formatted_chunks = []

        for r in runs:
            text = r['text']
            if not text:
                continue

            r_id = r.get('r_id')
            target = rel_map.get(r_id, "") if r_id else ""

            # Check if this run is an embedded citation hyperlink
            cite_key = None
            if r_id and r_id in self.citation_map:
                cite_key = self.citation_map[r_id]
            elif target:
                if target in self.citation_map:
                    cite_key = self.citation_map[target]
                else:
                    norm_target = clean_doi(target)
                    if norm_target and norm_target in self.citation_map:
                        cite_key = self.citation_map[norm_target]
                    else:
                        doi_match = re.search(r'(10\.\d{4,9}/[^\s]+)', target)
                        if doi_match:
                            doi = clean_doi(doi_match.group(1))
                            cite_key = self.citation_map.get(doi)
            elif text.strip() in self.citation_map:
                cite_key = self.citation_map[text.strip()]

            if cite_key:
                formatted_chunks.append(f"\\cite{{{cite_key}}}")
            else:
                # Escape special characters
                safe_text = sanitize_latex_text(text)
                if r.get('bold') and r.get('italic'):
                    formatted_chunks.append(f"\\textbf{{\\textit{{{safe_text}}}}}")
                elif r.get('bold'):
                    formatted_chunks.append(f"\\textbf{{{safe_text}}}")
                elif r.get('italic'):
                    formatted_chunks.append(f"\\textit{{{safe_text}}}")
                else:
                    formatted_chunks.append(safe_text)

        raw_latex = "".join(formatted_chunks)

        # Clean multiple spaces and ensure clean punctuation after \cite{}
        raw_latex = re.sub(r'\s*(\\cite\{[^\}]+\})\s*', r' \1 ', raw_latex)
        raw_latex = re.sub(r'\s+([,.;:\?!])', r'\1', raw_latex)
        return raw_latex.strip()


def convert_docx_to_latex(
    docx_path: str,
    output_tex: Optional[str] = None,
    citation_map: Optional[Dict[str, str]] = None,
    chapter_title: Optional[str] = None,
    chapter_label: Optional[str] = None,
) -> str:
    """Convenience function for DocxConverter."""
    converter = DocxConverter(citation_map=citation_map)
    return converter.convert(
        docx_path=docx_path,
        output_tex=output_tex,
        as_chapter=True,
        chapter_title=chapter_title,
        chapter_label=chapter_label,
    )
