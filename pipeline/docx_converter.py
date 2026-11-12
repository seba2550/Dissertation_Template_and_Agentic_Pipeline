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

        self._doc_base = os.path.basename(docx_path)
        elements, rel_map = self._extract_elements(docx_path)
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

        pending_table_caption = None

        for idx, elem in enumerate(elements):
            if elem.get('type') == 'table':
                table_latex = self._format_table(elem, caption=pending_table_caption)
                if table_latex:
                    latex_lines.append(table_latex)
                    latex_lines.append("")
                pending_table_caption = None
                continue

            para = elem
            style = para.get('style', '').lower()
            text = para.get('text', '').strip()
            runs = para.get('runs', [])

            if not text:
                continue

            # Check if this paragraph is a table caption for an upcoming table
            next_elem = elements[idx + 1] if idx + 1 < len(elements) else None
            if next_elem and next_elem.get('type') == 'table' and ('caption' in style or re.match(r'^Table\s+\d', text, re.IGNORECASE)):
                pending_table_caption = text
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

    def _extract_elements(self, docx_path: str) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
        """Extracts structured paragraph and table objects along with relationship mapping."""
        rel_map: Dict[str, str] = {}
        elements: List[Dict[str, Any]] = []

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

                # Iterate through body children (paragraphs and tables in document order)
                body = root.find(f'{{{W_NS}}}body')
                if body is not None:
                    for child in body:
                        if child.tag == f'{{{W_NS}}}p':
                            para_info = self._parse_paragraph_node(child)
                            elements.append(para_info)
                        elif child.tag == f'{{{W_NS}}}tbl':
                            tbl_info = self._parse_table_node(child)
                            elements.append(tbl_info)

        return elements, rel_map

    def _parse_table_node(self, tbl_node: ET.Element) -> Dict[str, Any]:
        """Parses a <w:tbl> node into structured rows and cells."""
        rows = []
        for tr in tbl_node.findall(f'{{{W_NS}}}tr'):
            row = []
            for tc in tr.findall(f'{{{W_NS}}}tc'):
                cell_texts = []
                for p in tc.findall(f'{{{W_NS}}}p'):
                    for r in p.findall(f'{{{W_NS}}}r'):
                        for t in r.findall(f'{{{W_NS}}}t'):
                            if t.text:
                                cell_texts.append(t.text)
                row.append(" ".join(cell_texts).strip())
            rows.append(row)
        return {
            'type': 'table',
            'rows': rows,
        }

    def _format_table(self, table_info: Dict[str, Any], caption: Optional[str] = None) -> str:
        """Formats a table into rubric-compliant LaTeX tabular environment with caption above."""
        rows = table_info.get('rows', [])
        if not rows:
            return ""
        col_count = max(len(r) for r in rows) if rows else 1
        col_align = "l" + "c" * (col_count - 1)

        latex = ["\\begin{table}[htbp]", "  \\centering"]
        if caption:
            c_match = re.match(r'^(Table\s+[\d\.]+)[:\.\s]*(.*)$', caption, re.IGNORECASE)
            if c_match:
                cap_text = c_match.group(2).strip() or caption
                latex.append(f"  \\caption{{{sanitize_latex_text(cap_text)}}}")
            else:
                latex.append(f"  \\caption{{{sanitize_latex_text(caption)}}}")
        latex.append(f"  \\begin{{tabular}}{{{col_align}}}")
        latex.append("    \\toprule")

        # Header row
        if rows:
            hdr = rows[0]
            hdr_cells = [f"\\textbf{{{sanitize_latex_text(c)}}}" for c in hdr]
            while len(hdr_cells) < col_count:
                hdr_cells.append("")
            latex.append("    " + " & ".join(hdr_cells) + " \\\\")
            latex.append("    \\midrule")

        # Data rows
        for row in rows[1:]:
            row_cells = [sanitize_latex_text(c) for c in row]
            while len(row_cells) < col_count:
                row_cells.append("")
            latex.append("    " + " & ".join(row_cells) + " \\\\")

        latex.append("    \\bottomrule")
        latex.append("  \\end{tabular}")
        latex.append("\\end{table}")
        return "\n".join(latex)

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
            'type': 'paragraph',
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

    def _format_text_with_inline_citations(self, text: str) -> str:
        """
        Detects inline DOIs and URLs within a text run, protects them from LaTeX escaping,
        and converts them to \\cite{...} if present in citation_map.
        """
        placeholders = {}
        token_idx = 0

        # 1. Match parenthesized or bracketed DOIs: (10.xxx) or [10.xxx] or (doi: 10.xxx)
        def repl_bracketed_doi(m):
            nonlocal token_idx
            raw = m.group(1)
            cd = clean_doi(raw)
            key = self.citation_map.get(cd) or self.citation_map.get(raw)
            if key:
                token_idx += 1
                ph = f"@@CITETOKEN{token_idx}@@"
                placeholders[ph] = f"\\cite{{{key}}}"
                return ph
            return m.group(0)

        text = re.sub(r'[\(\[]\s*(?:doi:\s*)?(10\.\d{4,9}/[^\s,;\)\]\}]+)\s*[\)\]]', repl_bracketed_doi, text, flags=re.IGNORECASE)

        # 2. Match URLs
        def repl_url(m):
            nonlocal token_idx
            raw = m.group(0).rstrip('.,;:')
            trailing = m.group(0)[len(raw):]
            key = self.citation_map.get(raw) or self.citation_map.get(clean_doi(raw))
            if key:
                token_idx += 1
                ph = f"@@CITETOKEN{token_idx}@@"
                placeholders[ph] = f"\\cite{{{key}}}"
                return ph + trailing
            return m.group(0)

        text = re.sub(r'https?://[^\s<>"\'\)\]\}]+', repl_url, text)

        # 3. Match bare DOIs (after URLs, so DOIs inside URLs are handled as whole URLs): 10.xxx/yyy
        def repl_bare_doi(m):
            nonlocal token_idx
            full_match = m.group(0)
            trailing_punct = re.search(r'[.,;:!?]+$', full_match)
            punct = trailing_punct.group(0) if trailing_punct else ""
            raw = full_match[:-len(punct)] if punct else full_match
            cd = clean_doi(raw)
            key = self.citation_map.get(cd) or self.citation_map.get(raw)
            if key:
                token_idx += 1
                ph = f"@@CITETOKEN{token_idx}@@"
                placeholders[ph] = f"\\cite{{{key}}}"
                return ph + punct
            return full_match

        text = re.sub(r'\b10\.\d{4,9}/[^\s,;\)\]\}]+', repl_bare_doi, text)

        # 4. Sanitize text for LaTeX
        sanitized = sanitize_latex_text(text)

        # 5. Restore citation commands
        for ph, cite_cmd in placeholders.items():
            sanitized = sanitized.replace(ph, cite_cmd)

        return sanitized

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
            # 1. Prioritize target URL/DOI first (globally unique; prevents cross-document rId collision)
            if target:
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

            # 2. Fallback to r_id only if target was not resolved
            # Use the document-scoped key ("chapter.docx::rId5"); bare rIds collide across documents.
            if not cite_key and r_id:
                base = getattr(self, '_doc_base', None)
                scoped = f"{base}::{r_id}" if base else None
                if scoped and scoped in self.citation_map:
                    cite_key = self.citation_map[scoped]
                elif r_id in self.citation_map:
                    cite_key = self.citation_map[r_id]

            # 3. Exact match of run text in citation map
            if not cite_key and text.strip() in self.citation_map:
                cite_key = self.citation_map[text.strip()]

            if cite_key:
                formatted_chunks.append(f"\\cite{{{cite_key}}}")
            else:
                safe_text = self._format_text_with_inline_citations(text)
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
