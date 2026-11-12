"""
pipeline.utils
==============
General helper utilities for the dissertation pipeline:
- BibTeX parsing, cleaning, serialization
- DOCX XML namespace handling
- DOI / PMID normalization
- Text manipulation & LaTeX escaping
"""

import re
import os
from typing import Dict, List, Optional, Tuple, Any

# WordprocessingML XML Namespaces
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

NAMESPACES = {
    "w": W_NS,
    "r": R_NS,
    "rel": PKG_REL_NS,
}


def clean_doi(doi: str) -> str:
    """Normalize a DOI string by removing prefixes, enclosing braces/quotes/parens, trailing punctuation, and bioRxiv version suffix."""
    if not doi:
        return ""
    doi = doi.strip().strip("({}'\"")
    doi = re.sub(r'^(https?://(dx\.)?doi\.org/|doi:\s*)', '', doi, flags=re.IGNORECASE)
    while doi and doi[-1] in '.,;:}]':
        doi = doi[:-1]
    while doi.endswith(')') and doi.count('(') < doi.count(')'):
        doi = doi[:-1]
    if '10.1101/' in doi:
        doi = re.sub(r'v\d+$', '', doi)
    return doi.strip().strip("({}'\"")


def clean_pmid(pmid: str) -> str:
    """Normalize a PMID string."""
    if not pmid:
        return ""
    m = re.search(r'\b(\d{1,9})\b', str(pmid))
    return m.group(1) if m else ""


def clean_pmcid(pmcid: str) -> str:
    """Normalize a PMCID string (e.g. PMC1234567)."""
    if not pmcid:
        return ""
    m = re.search(r'\b(PMC\d+)\b', str(pmcid), flags=re.IGNORECASE)
    return m.group(1).upper() if m else ""


def extract_bibtex_field(raw_entry: str, field: str) -> Optional[str]:
    """
    Extracts a BibTeX field value handling balanced braces, quotes, and bare values.
    Prevents corruption when a field is the last element before the record closing brace.
    """
    pattern = re.compile(rf'\b{field}\s*=\s*', re.IGNORECASE)
    m = pattern.search(raw_entry)
    if not m:
        return None
    start = m.end()
    if start >= len(raw_entry):
        return None
    char = raw_entry[start]
    if char == '{':
        depth = 0
        for i in range(start, len(raw_entry)):
            if raw_entry[i] == '{':
                depth += 1
            elif raw_entry[i] == '}':
                depth -= 1
                if depth == 0:
                    val = raw_entry[start + 1:i].strip()
                    return re.sub(r'\s+', ' ', val)
    elif char == '"':
        for i in range(start + 1, len(raw_entry)):
            if raw_entry[i] == '"' and raw_entry[i - 1] != '\\':
                val = raw_entry[start + 1:i].strip()
                return re.sub(r'\s+', ' ', val)
    else:
        m_bare = re.match(r'([^\s,}]+)', raw_entry[start:])
        if m_bare:
            return m_bare.group(1).strip()
    return None


def parse_bibtex_file(bib_path: str) -> Dict[str, Dict[str, str]]:
    """
    Parses a .bib BibTeX file into a dictionary of entries:
    {
       citekey: {
          'entry_type': 'article',
          'citekey': citekey,
          'title': '...',
          'author': '...',
          'doi': '...',
          'raw': '...'
       }
    }
    """
    if not os.path.isfile(bib_path):
        return {}

    entries: Dict[str, Dict[str, str]] = {}
    with open(bib_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    # Match @type{key, ...}
    pattern = re.compile(r'@([a-zA-Z]+)\s*\{\s*([^,]+),', re.MULTILINE)
    matches = list(pattern.finditer(content))

    for i, m in enumerate(matches):
        entry_type = m.group(1).lower()
        citekey = m.group(2).strip()
        start_idx = m.start()
        end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(content)

        raw_chunk = content[start_idx:end_idx].strip()
        # Find closing brace if before next match
        last_brace = raw_chunk.rfind('}')
        if last_brace != -1:
            raw_entry = raw_chunk[:last_brace + 1]
        else:
            raw_entry = raw_chunk

        data: Dict[str, str] = {
            'entry_type': entry_type,
            'citekey': citekey,
            'raw': raw_entry,
        }

        # Extract common fields
        for field in ['title', 'author', 'journal', 'year', 'volume', 'pages', 'doi', 'url', 'pmid', 'note', 'eprint', 'howpublished']:
            val = extract_bibtex_field(raw_entry, field)
            if val is not None:
                data[field] = val

        if 'doi' in data:
            data['doi_normalized'] = clean_doi(data['doi'])

        entries[citekey] = data

    return entries


KNOWN_ACRONYMS = {
    'DNA', 'RNA', 'CPG', 'MEQTL', 'EQTL', 'AD', 'GWAS', 'EWAS',
    'PRS', 'PCA', 'SNP', 'SNPS', 'AUC', 'MAE', 'MAGENTA', 'LD', 'UCSF',
    'PCR', 'MRNA', 'TCGA', 'ENCODE', 'GEO', 'PMID', 'DOI'
}
ACRONYM_MAP = {
    'DNA': 'DNA', 'RNA': 'RNA', 'CPG': 'CpG', 'MEQTL': 'meQTL', 'EQTL': 'eQTL',
    'AD': 'AD', 'GWAS': 'GWAS', 'EWAS': 'EWAS', 'PRS': 'PRS', 'PCA': 'PCA',
    'SNP': 'SNP', 'SNPS': 'SNPs', 'AUC': 'AUC', 'MAE': 'MAE', 'MAGENTA': 'MAGENTA',
    'LD': 'LD', 'UCSF': 'UCSF', 'PCR': 'PCR', 'MRNA': 'mRNA', 'TCGA': 'TCGA',
    'ENCODE': 'ENCODE', 'GEO': 'GEO', 'PMID': 'PMID', 'DOI': 'DOI'
}


def to_sentence_case(text: str) -> str:
    """
    Convert heading text to Sentence Case (Capitalize first word, lowercase standard words
    except proper nouns, biological acronyms, or mixed-case identifiers).
    """
    if not text:
        return ""
    words = text.split()
    if not words:
        return ""

    result = []
    for i, w in enumerate(words):
        upper_w = re.sub(r'[^A-Za-z]', '', w).upper()
        if upper_w in KNOWN_ACRONYMS:
            result.append(ACRONYM_MAP.get(upper_w, w))
        elif re.search(r'[a-z][A-Z]', w):
            # Mixed-case term (e.g. meQTL, mRNA, miRNA, miR29)
            result.append(w)
        elif i == 0:
            result.append(w.capitalize())
        else:
            result.append(w.lower())

    return " ".join(result)


def sanitize_latex_text(text: str) -> str:
    """
    Escape special LaTeX characters in plain text.
    """
    replacements = [
        ('&', r'\&'),
        ('%', r'\%'),
        ('$', r'\$'),
        ('#', r'\#'),
        ('_', r'\_'),
        ('{', r'\{'),
        ('}', r'\}'),
        ('~', r'\textasciitilde{}'),
        ('^', r'\textasciicircum{}'),
    ]
    for char, escaped in replacements:
        text = text.replace(char, escaped)
    return text
