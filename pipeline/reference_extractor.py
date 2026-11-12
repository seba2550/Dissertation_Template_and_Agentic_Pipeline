"""
pipeline.reference_extractor
============================
Enhanced Reference Extractor & BibTeX Generator.
Extracts hyperlinks, relationships, and citations from Microsoft Word (.docx) documents,
resolves DOIs, PMIDs, PMCIDs, and academic URLs via local bibliography caches or online APIs,
and outputs clean, Zotero-ready BibTeX (.bib) files, DOI lists (.txt), and citation maps (.json).

Zero external dependencies: uses Python standard library only.
"""

import os
import sys
import re
import json
import zipfile
import xml.etree.ElementTree as ET
import urllib.request
import urllib.parse
import ssl
import time
from typing import Dict, List, Optional, Set, Tuple, Any

from .utils import (
    clean_doi,
    clean_pmid,
    clean_pmcid,
    parse_bibtex_file,
    W_NS,
    R_NS,
    PKG_REL_NS,
)

# SSL context for compatibility across systems
ssl_context = ssl._create_unverified_context()
DEFAULT_USER_AGENT = "DocxReferenceExtractor/2.0"


class ReferenceExtractor:
    """
    Modular reference extractor that parses .docx files, queries Crossref/PubMed,
    and supports local .bib cache lookup for offline and high-performance operation.
    """

    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        local_bib_paths: Optional[List[str]] = None,
        timeout: int = 8,
    ):
        self.user_agent = user_agent
        self.timeout = timeout
        self.local_entries: Dict[str, Dict[str, str]] = {}
        self.doi_to_local_entry: Dict[str, Dict[str, str]] = {}
        self.pmid_to_local_entry: Dict[str, Dict[str, str]] = {}
        self.pmcid_to_local_entry: Dict[str, Dict[str, str]] = {}
        self.url_to_local_entry: Dict[str, Dict[str, str]] = {}
        self.key_to_local_entry: Dict[str, Dict[str, str]] = {}

        if local_bib_paths:
            for p in local_bib_paths:
                self.load_local_bib(p)

    def load_local_bib(self, bib_path: str):
        """Load and index entries from an existing .bib file by DOI, PMID, PMCID, URL, and citekey."""
        entries = parse_bibtex_file(bib_path)
        for key, entry in entries.items():
            self.local_entries[key] = entry
            self.key_to_local_entry[key.lower()] = entry
            
            doi_norm = entry.get('doi_normalized') or clean_doi(entry.get('doi', ''))
            if doi_norm:
                self.doi_to_local_entry[doi_norm.lower()] = entry

            pmid = clean_pmid(entry.get('pmid', ''))
            if pmid:
                self.pmid_to_local_entry[pmid] = entry

            url = entry.get('url', '').strip()
            if url:
                self.url_to_local_entry[url.lower()] = entry
                norm_u = re.sub(r'^https?://', '', url.lower()).rstrip('/')
                self.url_to_local_entry[norm_u] = entry

            # Extract any embedded PMCID or DOI in other fields (note, eprint, howpublished)
            for fld in ['note', 'eprint', 'howpublished', 'url', 'pages', 'journal']:
                val = entry.get(fld, '')
                pmc_m = re.search(r'\b(PMC\d+)\b', val, re.IGNORECASE)
                if pmc_m:
                    self.pmcid_to_local_entry[pmc_m.group(1).upper()] = entry
                doi_m = re.search(r'(10\.\d{4,9}/[^\s,]+)', val)
                if doi_m:
                    d_norm = clean_doi(doi_m.group(1)).lower()
                    if d_norm and d_norm not in self.doi_to_local_entry:
                        self.doi_to_local_entry[d_norm] = entry

    def extract_links_from_docx(self, docx_path: str) -> Tuple[List[str], List[str], Dict[str, str]]:
        """
        Extracts all hyperlinks, raw DOIs, and an rId->target mapping from a .docx file.
        Returns: (sorted_urls, sorted_dois, rel_id_map)
        """
        if not os.path.isfile(docx_path):
            raise FileNotFoundError(f"File not found: {docx_path}")

        found_urls: Set[str] = set()
        found_dois: Set[str] = set()
        rel_id_map: Dict[str, str] = {}

        with zipfile.ZipFile(docx_path, 'r') as docx_zip:
            namelist = docx_zip.namelist()

            # 1. Parse all relationship files (word/_rels/*.rels)
            rel_files = [f for f in namelist if f.startswith('word/_rels/') and f.endswith('.rels')]
            for rel_file in rel_files:
                try:
                    xml_data = docx_zip.read(rel_file)
                    root = ET.fromstring(xml_data)
                    for elem in root.iter():
                        if elem.tag.endswith('Relationship'):
                            r_id = elem.attrib.get('Id', '')
                            target = elem.attrib.get('Target', '').strip()
                            if r_id and target:
                                rel_id_map[r_id] = target

                            if target.startswith('http://') or target.startswith('https://'):
                                found_urls.add(target)
                            elif target.startswith('doi:') or target.startswith('10.'):
                                cleaned = clean_doi(target)
                                if cleaned:
                                    found_dois.add(cleaned)
                except Exception:
                    pass

            # 2. Parse document text, footnotes, and endnotes
            text_files = [f for f in namelist if f in ['word/document.xml', 'word/footnotes.xml', 'word/endnotes.xml']]
            for tfile in text_files:
                try:
                    xml_data = docx_zip.read(tfile)
                    root = ET.fromstring(xml_data)

                    # Extract all text
                    text_fragments = []
                    for elem in root.iter():
                        if elem.tag.endswith('}t') and elem.text:
                            text_fragments.append(elem.text)

                    full_text = " ".join(text_fragments)

                    # Match plaintext URLs
                    raw_urls = re.findall(r'https?://[^\s<>"\'\)\]\}]+', full_text)
                    for u in raw_urls:
                        u_clean = re.sub(r'[\.,;:\)\]\}]+$', '', u).strip()
                        if u_clean:
                            found_urls.add(u_clean)

                    # Match plaintext DOIs
                    raw_dois = re.findall(r'\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+', full_text)
                    for d in raw_dois:
                        d_clean = clean_doi(d)
                        if d_clean:
                            found_dois.add(d_clean)

                except Exception:
                    pass

        return sorted(list(found_urls)), sorted(list(found_dois)), rel_id_map

    def resolve_url_to_identifier(self, url: str) -> Dict[str, str]:
        """
        Parses a URL to extract an explicit DOI, PMID, PMCID, or query identifier.
        Supports standard publisher URLs (Nature, BioRxiv, eLife, CSHLP, Aging, PubMed, PMC, arXiv).
        """
        # 1. Direct DOI embedded in URL path
        doi_match = re.search(r'(10\.\d{4,9}/[^\s\?\#\&]+)', url)
        if doi_match:
            doi = clean_doi(doi_match.group(1))
            return {'type': 'doi', 'id': doi}

        # 2. Nature URL format
        nature_match = re.search(r'nature\.com/articles/([a-zA-Z0-9\-_]+)', url)
        if nature_match:
            art_id = nature_match.group(1)
            return {'type': 'doi', 'id': f'10.1038/{art_id}'}

        # 3. BioRxiv / MedRxiv URL format
        biorxiv_match = re.search(r'(?:biorxiv|medrxiv)\.org/content/(10\.\d{4,9}/[^\s\?\#\&v]+)', url)
        if biorxiv_match:
            doi = clean_doi(biorxiv_match.group(1))
            return {'type': 'doi', 'id': doi}

        # 4. Aging (Albany NY) URL format
        aging_match = re.search(r'aging-us\.com/article/(\d+)', url)
        if aging_match:
            return {'type': 'doi', 'id': f'10.18632/aging.{aging_match.group(1)}'}

        # 5. eLife URL format
        elife_match = re.search(r'elifesciences\.org/articles/(\d+)', url)
        if elife_match:
            return {'type': 'doi', 'id': f'10.7554/eLife.{elife_match.group(1)}'}

        # 6. Cold Spring Harbor (Genes & Development, Genome Research)
        csh_gad = re.search(r'genesdev\.cshlp\.org/content/([^/]+)/([^/]+)/([^/.]+)', url)
        if csh_gad:
            return {'type': 'doi', 'id': f'10.1101/gad.{csh_gad.group(1)}.{csh_gad.group(2)}.{csh_gad.group(3)}'}

        csh_gr = re.search(r'genome\.cshlp\.org/content/([^/]+)/([^/]+)/([^/.]+)', url)
        if csh_gr:
            return {'type': 'doi', 'id': f'10.1101/gr.{csh_gr.group(1)}.{csh_gr.group(2)}.{csh_gr.group(3)}'}

        # 7. Annual Reviews
        annurev_match = re.search(r'annualreviews\.org/.*(annurev-[a-z0-9\-]+)', url)
        if annurev_match:
            return {'type': 'doi', 'id': f'10.1146/{annurev_match.group(1)}'}

        # 8. PubMed URL
        pubmed_match = re.search(r'pubmed\.ncbi\.nlm\.nih\.gov/(\d+)', url)
        if pubmed_match:
            return {'type': 'pmid', 'id': pubmed_match.group(1)}

        # 9. PubMed Central URL
        pmc_match = re.search(r'(?:pmc.*?/articles/|/pmc/articles/)(PMC\d+)', url, re.IGNORECASE)
        if pmc_match:
            return {'type': 'pmcid', 'id': pmc_match.group(1).upper()}

        # 10. arXiv URL format
        arxiv_match = re.search(r'arxiv\.org/(?:abs|pdf)/(\d+\.\d+)', url)
        if arxiv_match:
            return {'type': 'arxiv', 'id': arxiv_match.group(1)}

        # 11. ScienceDirect / Elsevier / Cell PII
        pii_match = re.search(r'(?:sciencedirect\.com/science/article/pii/|cell\.com/[^/]+/(?:fulltext|abstract)/)([A-Z0-9\(\)\-]+)', url)
        if pii_match:
            return {'type': 'pii', 'id': pii_match.group(1)}

        # 12. JAMA Network
        jama_match = re.search(r'jamanetwork\.com/journals/([a-z]+)/fullarticle/(\d+)', url)
        if jama_match:
            journal, art_id = jama_match.groups()
            return {'type': 'jama', 'id': f'{journal}_{art_id}'}

        return {'type': 'url', 'id': url}

    def fetch_bibtex_from_doi(self, doi: str) -> Optional[str]:
        """
        Fetches BibTeX record for a DOI, first checking local caches, then Crossref / doi.org.
        """
        cleaned = clean_doi(doi)
        norm_key = cleaned.lower()

        # Check local cache first
        if norm_key in self.doi_to_local_entry:
            return self.doi_to_local_entry[norm_key]['raw']

        # Attempt online fetch
        doi_encoded = urllib.parse.quote(cleaned)
        url = f"https://api.crossref.org/works/{doi_encoded}/transform/application/x-bibtex"
        headers = {'User-Agent': self.user_agent}
        req = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(req, context=ssl_context, timeout=self.timeout) as response:
                bibtex = response.read().decode('utf-8').strip()
                if bibtex.startswith('@'):
                    return bibtex
        except Exception:
            # Fallback to doi.org direct negotiation
            try:
                direct_url = f"https://doi.org/{cleaned}"
                direct_req = urllib.request.Request(
                    direct_url,
                    headers={'Accept': 'application/x-bibtex', 'User-Agent': self.user_agent}
                )
                with urllib.request.urlopen(direct_req, context=ssl_context, timeout=self.timeout) as response:
                    bibtex = response.read().decode('utf-8').strip()
                    if bibtex.startswith('@'):
                        return bibtex
            except Exception:
                pass

        return None

    def fetch_metadata_from_pubmed(self, pmid: str) -> Tuple[Optional[str], str]:
        """
        Fetches citation metadata from NCBI E-utilities for a given PMID.
        Returns: (bibtex_string, doi_if_found)
        """
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={pmid}&retmode=json"
        headers = {'User-Agent': self.user_agent}
        req = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(req, context=ssl_context, timeout=self.timeout) as response:
                data = json.loads(response.read().decode('utf-8'))
                result = data.get('result', {}).get(str(pmid), {})
                if result:
                    title = result.get('title', 'Unknown Title').rstrip('.')
                    authors_list = [a.get('name', '') for a in result.get('authors', []) if a.get('name')]
                    author_str = ' and '.join(authors_list) if authors_list else 'Unknown'
                    journal = result.get('source', '')
                    pubdate = result.get('pubdate', '')
                    year_match = re.search(r'\b(19\d\d|20\d\d)\b', pubdate)
                    year = year_match.group(1) if year_match else '2024'
                    volume = result.get('volume', '')
                    pages = result.get('pages', '')

                    doi = ""
                    for aid in result.get('articleids', []):
                        if aid.get('idtype') == 'doi':
                            doi = clean_doi(aid.get('value', ''))
                            break

                    first_author = authors_list[0].split()[0] if authors_list else f"pmid_{pmid}"
                    citekey = re.sub(r'[^a-zA-Z0-9_]', '', f"{first_author}_{year}")

                    bibtex = f"""@article{{{citekey},
  author = {{{author_str}}},
  title = {{{title}}},
  journal = {{{journal}}},
  year = {{{year}}},
  volume = {{{volume}}},
  pages = {{{pages}}},
  doi = {{{doi}}},
  note = {{PMID: {pmid}}}
}}"""
                    return bibtex, doi
        except Exception:
            pass

        return None, ""

    def fetch_metadata_from_pmcid(self, pmcid: str) -> Tuple[Optional[str], str]:
        """
        Resolves a PMCID (e.g. PMC8086086) via local bib caches or NCBI PMC ID converter API.
        Returns: (bibtex_string, doi_if_found)
        """
        pmc_norm = clean_pmcid(pmcid)
        if pmc_norm in self.pmcid_to_local_entry:
            entry = self.pmcid_to_local_entry[pmc_norm]
            return entry['raw'], clean_doi(entry.get('doi', ''))

        # Attempt online NCBI PMC ID converter API
        try:
            url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids={pmc_norm}&format=json"
            headers = {'User-Agent': self.user_agent}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=ssl_context, timeout=self.timeout) as response:
                data = json.loads(response.read().decode('utf-8'))
                records = data.get('records', [])
                if records:
                    rec = records[0]
                    doi = clean_doi(rec.get('doi', ''))
                    pmid = clean_pmid(rec.get('pmid', ''))
                    if doi:
                        bib = self.fetch_bibtex_from_doi(doi)
                        if bib:
                            return bib, doi
                    if pmid:
                        return self.fetch_metadata_from_pubmed(pmid)
        except Exception:
            pass

        return None, ""

    def create_fallback_bibtex(
        self,
        url_or_doi: str,
        key_prefix: str = "ref",
        existing_keys: Optional[Set[str]] = None,
    ) -> Tuple[str, str]:
        """
        Creates a clean, valid BibTeX @misc entry for unresolvable URLs or offline citations.
        Returns (citekey, bibtex_string), ensuring citekey uniqueness across entries.
        """
        clean_name = re.sub(r'https?://', '', url_or_doi)
        clean_name = re.sub(r'[^a-zA-Z0-9]', '_', clean_name).strip('_')
        base_slug = clean_name[:28] if clean_name else "entry"
        base_key = f"{key_prefix}_{base_slug}"
        citekey = base_key

        if existing_keys is not None:
            counter = 1
            while citekey in existing_keys:
                counter += 1
                citekey = f"{base_key}_{counter}"
            existing_keys.add(citekey)

        bibtex = f"""@misc{{{citekey},
  title = {{{url_or_doi}}},
  url = {{{url_or_doi}}},
  howpublished = {{\\url{{{url_or_doi}}}}},
  note = {{Extracted from manuscript}}
}}"""
        return citekey, bibtex

    def process(
        self,
        docx_file: Any,  # str or List[str]
        output_bib: str = "references.bib",
        output_dois: str = "doi_list.txt",
        output_map: Optional[str] = None,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes reference extraction pipeline on one or more .docx files.
        Outputs consolidated .bib, .txt, and returns a summary dict including citation mapping.
        """
        if isinstance(docx_file, (list, tuple)):
            docx_files = list(docx_file)
        else:
            docx_files = [docx_file]

        all_urls: Set[str] = set()
        all_dois: Set[str] = set()
        combined_rel_map: Dict[str, str] = {}

        for df in docx_files:
            urls, direct_dois, rel_id_map = self.extract_links_from_docx(df)
            all_urls.update(urls)
            all_dois.update(direct_dois)
            base = os.path.basename(df)
            for r_id, target in rel_id_map.items():
                combined_rel_map[f"{base}::{r_id}"] = target
                # Bare rIds are only unambiguous for single-document runs
                if len(docx_files) == 1:
                    combined_rel_map[r_id] = target

        resolved_bibtex: Dict[str, str] = {}
        resolved_dois: Set[str] = set(all_dois)
        unresolved_urls: List[str] = []
        citation_map: Dict[str, str] = {}  # maps original target/DOI/URL to citekey
        active_keys: Set[str] = set()

        # 1. Process explicit DOIs
        for doi in sorted(list(all_dois)):
            bib = self.fetch_bibtex_from_doi(doi)
            if bib:
                m_key = re.search(r'@[a-zA-Z]+\{([^,]+),', bib)
                key = m_key.group(1).strip() if m_key else doi
                resolved_bibtex[key] = bib
                active_keys.add(key)
                citation_map[doi] = key
                citation_map[f"https://doi.org/{doi}"] = key
                citation_map[f"http://dx.doi.org/{doi}"] = key
            else:
                key, fallback_bib = self.create_fallback_bibtex(
                    f"10.{doi}" if not doi.startswith("10.") else doi,
                    existing_keys=active_keys,
                )
                resolved_bibtex[key] = fallback_bib
                citation_map[doi] = key

        # 2. Process URLs
        for url in sorted(list(all_urls)):
            ident = self.resolve_url_to_identifier(url)
            itype = ident['type']
            ival = ident['id']

            if itype == 'doi':
                resolved_dois.add(ival)
                bib = self.fetch_bibtex_from_doi(ival)
                if bib:
                    m_key = re.search(r'@[a-zA-Z]+\{([^,]+),', bib)
                    key = m_key.group(1).strip() if m_key else ival
                    resolved_bibtex[key] = bib
                    active_keys.add(key)
                    citation_map[url] = key
                    citation_map[ival] = key
                    citation_map[f"https://doi.org/{ival}"] = key
                else:
                    key, fallback_bib = self.create_fallback_bibtex(url, existing_keys=active_keys)
                    resolved_bibtex[key] = fallback_bib
                    citation_map[url] = key
                    citation_map[ival] = key
                    unresolved_urls.append(url)

            elif itype == 'pmid':
                # Check local cache first for PMID
                bib = None
                doi = ""
                if ival in self.pmid_to_local_entry:
                    entry = self.pmid_to_local_entry[ival]
                    bib = entry['raw']
                    doi = clean_doi(entry.get('doi_normalized') or entry.get('doi', ''))
                else:
                    bib, doi = self.fetch_metadata_from_pubmed(ival)

                if bib:
                    m_key = re.search(r'@[a-zA-Z]+\{([^,]+),', bib)
                    key = m_key.group(1).strip() if m_key else f"pmid_{ival}"
                    resolved_bibtex[key] = bib
                    active_keys.add(key)
                    citation_map[url] = key
                    citation_map[ival] = key
                    if doi:
                        resolved_dois.add(doi)
                        citation_map[doi] = key
                        citation_map[f"https://doi.org/{doi}"] = key
                else:
                    key, fallback_bib = self.create_fallback_bibtex(url, existing_keys=active_keys)
                    resolved_bibtex[key] = fallback_bib
                    citation_map[url] = key
                    unresolved_urls.append(url)

            elif itype == 'pmcid':
                bib, doi = self.fetch_metadata_from_pmcid(ival)
                if bib:
                    m_key = re.search(r'@[a-zA-Z]+\{([^,]+),', bib)
                    key = m_key.group(1).strip() if m_key else f"pmc_{ival}"
                    resolved_bibtex[key] = bib
                    active_keys.add(key)
                    citation_map[url] = key
                    citation_map[ival] = key
                    if doi:
                        resolved_dois.add(doi)
                        citation_map[doi] = key
                        citation_map[f"https://doi.org/{doi}"] = key
                else:
                    key, fallback_bib = self.create_fallback_bibtex(url, existing_keys=active_keys)
                    resolved_bibtex[key] = fallback_bib
                    citation_map[url] = key
                    unresolved_urls.append(url)

            else:
                # Check if URL matches cached entries
                norm_u = re.sub(r'^https?://', '', url.lower()).rstrip('/')
                cached_match = self.url_to_local_entry.get(url.lower()) or self.url_to_local_entry.get(norm_u)
                if cached_match:
                    key = cached_match['citekey']
                    resolved_bibtex[key] = cached_match['raw']
                    active_keys.add(key)
                    citation_map[url] = key
                    doi_c = clean_doi(cached_match.get('doi_normalized') or cached_match.get('doi', ''))
                    if doi_c:
                        resolved_dois.add(doi_c)
                        citation_map[doi_c] = key
                else:
                    key, fallback_bib = self.create_fallback_bibtex(url, existing_keys=active_keys)
                    resolved_bibtex[key] = fallback_bib
                    citation_map[url] = key
                    unresolved_urls.append(url)

        # 3. Map all Word Relationship IDs to resolved citekeys
        for r_id_key, target in combined_rel_map.items():
            if target in citation_map:
                citation_map[r_id_key] = citation_map[target]
            else:
                c_doi = clean_doi(target)
                if c_doi and c_doi in citation_map:
                    citation_map[r_id_key] = citation_map[c_doi]

        # 4. Write BibTeX file
        os.makedirs(os.path.dirname(os.path.abspath(output_bib)) or ".", exist_ok=True)
        with open(output_bib, 'w', encoding='utf-8') as f:
            src_desc = os.path.basename(docx_files[0]) if len(docx_files) == 1 else f"{len(docx_files)} manuscripts"
            f.write("% =========================================================\n")
            f.write(f"% BibTeX Library generated from {src_desc}\n")
            f.write(f"% Total Entries: {len(resolved_bibtex)}\n")
            f.write("% =========================================================\n\n")
            f.write('\n\n'.join(resolved_bibtex.values()))
            f.write('\n')

        # 5. Write DOI list
        sorted_dois = sorted(list(resolved_dois))
        os.makedirs(os.path.dirname(os.path.abspath(output_dois)) or ".", exist_ok=True)
        with open(output_dois, 'w', encoding='utf-8') as f:
            for d in sorted_dois:
                f.write(f"{d}\n")

        # 6. Optionally save citation map
        if output_map:
            os.makedirs(os.path.dirname(os.path.abspath(output_map)) or ".", exist_ok=True)
            with open(output_map, 'w', encoding='utf-8') as f:
                json.dump(citation_map, f, indent=2)

        summary = {
            'docx_file': docx_files[0] if len(docx_files) == 1 else docx_files,
            'docx_files': docx_files,
            'total_extracted': len(resolved_bibtex),
            'formal_dois': len(sorted_dois),
            'fallbacks': len(unresolved_urls),
            'bib_file': output_bib,
            'doi_file': output_dois,
            'citation_map': citation_map,
            'entries': resolved_bibtex,
        }
        return summary


def extract_docx_references(
    docx_file: Any,  # str or List[str]
    output_bib: str = "references.bib",
    output_dois: str = "doi_list.txt",
    output_map: Optional[str] = None,
    email: Optional[str] = None,
    local_bib_paths: Optional[List[str]] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Convenience wrapper for ReferenceExtractor.process supporting one or multiple docx files."""
    user_agent = f"DocxReferenceExtractor/2.0 (mailto:{email})" if email else DEFAULT_USER_AGENT
    extractor = ReferenceExtractor(
        user_agent=user_agent,
        local_bib_paths=local_bib_paths,
    )
    return extractor.process(
        docx_file=docx_file,
        output_bib=output_bib,
        output_dois=output_dois,
        output_map=output_map,
        verbose=verbose,
    )
