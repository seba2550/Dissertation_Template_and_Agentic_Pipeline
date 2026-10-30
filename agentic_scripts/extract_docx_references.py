#!/usr/bin/env python3
"""
extract_docx_references.py
==========================
A lightweight, zero-dependency tool to extract hyperlinks and references from 
Microsoft Word (.docx) documents and convert them into a Zotero-ready BibTeX (.bib) 
database and DOI list.

Requirements:
- Python 3.7+ (No external pip packages required! Uses only Python standard library)
- Internet connection (to query Crossref and NCBI PubMed APIs)

Usage:
  python3 extract_docx_references.py manuscript.docx
  python3 extract_docx_references.py manuscript.docx -o my_library.bib --dois my_dois.txt

Author: Computational Biology & Informatics Workflow
"""

import sys
import os
import re
import json
import zipfile
import xml.etree.ElementTree as ET
import urllib.request
import urllib.parse
import ssl
import time
import argparse

# Ensure workspace root is in sys.path for pipeline imports
_script_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_script_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

# Bypass local SSL certificate validation issues on various OS environments
ssl_context = ssl._create_unverified_context()

# Common headers for polite API requests
DEFAULT_USER_AGENT = "DocxReferenceExtractor/1.0 (mailto:lab-tools@academic.edu)"


# ==============================================================================
# 1. DOCX HYPERLINK & TEXT EXTRACTION
# ==============================================================================

def extract_links_from_docx(docx_path):
    """
    Extracts all hyperlinks (embedded Word hyperlinks, relationship targets, 
    and plaintext URLs/DOIs) from a .docx file.
    """
    if not os.path.isfile(docx_path):
        raise FileNotFoundError(f"File not found: {docx_path}")

    found_urls = set()
    found_dois = set()

    with zipfile.ZipFile(docx_path, 'r') as docx_zip:
        namelist = docx_zip.namelist()

        # 1. Check all relationship XML files for external hyperlinks (e.g. document.xml.rels, footnotes.xml.rels)
        rel_files = [f for f in namelist if f.startswith('word/_rels/') and f.endswith('.rels')]
        for rel_file in rel_files:
            try:
                xml_data = docx_zip.read(rel_file)
                root = ET.fromstring(xml_data)
                for elem in root.iter():
                    if elem.tag.endswith('Relationship'):
                        target = elem.attrib.get('Target', '')
                        target_mode = elem.attrib.get('TargetMode', '')
                        if target.startswith('http://') or target.startswith('https://'):
                            found_urls.add(target.strip())
                        elif target.startswith('doi:') or target.startswith('10.'):
                            found_dois.add(re.sub(r'^doi:\s*', '', target).strip())
            except Exception as e:
                pass

        # 2. Check document text, footnotes, endnotes for plaintext URLs or DOIs
        text_files = [f for f in namelist if f in ['word/document.xml', 'word/footnotes.xml', 'word/endnotes.xml']]
        for tfile in text_files:
            try:
                xml_data = docx_zip.read(tfile)
                root = ET.fromstring(xml_data)
                # Extract all text nodes
                text_fragments = []
                for elem in root.iter():
                    if elem.tag.endswith('}t') and elem.text:
                        text_fragments.append(elem.text)
                
                full_text = ' '.join(text_fragments)

                # Match raw URLs
                raw_urls = re.findall(r'https?://[^\s<>"\)\]\}]+', full_text)
                for u in raw_urls:
                    # Clean trailing punctuation often attached from prose
                    u_clean = re.sub(r'[\.,;:\)]+$', '', u)
                    found_urls.add(u_clean.strip())

                # Match raw DOIs (e.g. 10.1038/s41588-023-01501-z)
                raw_dois = re.findall(r'\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+', full_text)
                for d in raw_dois:
                    d_clean = re.sub(r'[\.,;:\)]+$', '', d)
                    found_dois.add(d_clean.strip())

            except Exception as e:
                pass

    return sorted(list(found_urls)), sorted(list(found_dois))


# ==============================================================================
# 2. URL TO DOI / PMID RESOLUTION
# ==============================================================================

def resolve_url_to_identifier(url):
    """
    Parses a URL to extract an explicit DOI, PMID, or query identifier.
    """
    # 1. Direct DOI embedded in URL path
    # e.g., https://doi.org/10.1038/... or https://link.springer.com/article/10.1186/...
    doi_match = re.search(r'(10\.\d{4,9}/[^\s\?\#\&]+)', url)
    if doi_match:
        doi = doi_match.group(1)
        doi = re.sub(r'[\.,;:\)\]\}]+$', '', doi)
        return {'type': 'doi', 'id': doi}

    # 2. Nature URL format
    nature_match = re.search(r'nature\.com/articles/([a-zA-Z0-9\-_]+)', url)
    if nature_match:
        art_id = nature_match.group(1)
        return {'type': 'doi', 'id': f'10.1038/{art_id}'}

    # 3. BioRxiv / MedRxiv URL format
    biorxiv_match = re.search(r'(?:biorxiv|medrxiv)\.org/content/(10\.\d{4,9}/[^\s\?\#\&v]+)', url)
    if biorxiv_match:
        doi = re.sub(r'[\.,;:\)\]\}]+$', '', biorxiv_match.group(1))
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


# ==============================================================================
# 3. METADATA & BIBTEX FETCHING
# ==============================================================================

def fetch_bibtex_from_doi(doi, user_agent=DEFAULT_USER_AGENT):
    """
    Fetches clean BibTeX record from Crossref using Content Negotiation.
    """
    doi_encoded = urllib.parse.quote(doi)
    url = f"https://api.crossref.org/works/{doi_encoded}/transform/application/x-bibtex"
    headers = {'User-Agent': user_agent}
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, context=ssl_context, timeout=12) as response:
            bibtex = response.read().decode('utf-8').strip()
            if bibtex.startswith('@'):
                return bibtex
    except Exception:
        # Fallback to doi.org content negotiation directly
        try:
            direct_url = f"https://doi.org/{doi}"
            direct_req = urllib.request.Request(direct_url, headers={'Accept': 'application/x-bibtex', 'User-Agent': user_agent})
            with urllib.request.urlopen(direct_req, context=ssl_context, timeout=12) as response:
                bibtex = response.read().decode('utf-8').strip()
                if bibtex.startswith('@'):
                    return bibtex
        except Exception:
            pass

    return None


def fetch_metadata_from_pubmed(pmid, user_agent=DEFAULT_USER_AGENT):
    """
    Fetches citation metadata from NCBI E-utilities for a given PMID.
    """
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={pmid}&retmode=json"
    headers = {'User-Agent': user_agent}
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, context=ssl_context, timeout=12) as response:
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
                
                # Check for DOI in articleids
                doi = ""
                for aid in result.get('articleids', []):
                    if aid.get('idtype') == 'doi':
                        doi = aid.get('value', '')
                        break

                citekey = f"{authors_list[0].split()[0]}_{year}" if authors_list else f"pmid_{pmid}"
                citekey = re.sub(r'[^a-zA-Z0-9_]', '', citekey)

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


def create_fallback_bibtex(url, key_prefix="ref"):
    """
    Creates a valid BibTeX @misc entry for unresolvable URLs.
    """
    clean_key = re.sub(r'[^a-zA-Z0-9]', '_', url.replace('https://', '').replace('http://', ''))[:30]
    citekey = f"{key_prefix}_{clean_key}"
    return f"""@misc{{{citekey},
  title = {{{url}}},
  url = {{{url}}},
  howpublished = {{\\url{{{url}}}}},
  note = {{Accessed via document link}}
}}"""


# ==============================================================================
# 4. MAIN PROCESSING PIPELINE
# ==============================================================================

def process_docx_references(docx_file, output_bib="references.bib", output_dois="doi_list.txt", email=None, verbose=False):
    print(f"\n=======================================================")
    print(f" DOCX Reference Extractor & BibTeX Generator")
    print(f"=======================================================\n")
    print(f"[*] Analyzing Word Document: {docx_file}")

    user_agent = f"DocxReferenceExtractor/1.0 (mailto:{email})" if email else DEFAULT_USER_AGENT

    urls, direct_dois = extract_links_from_docx(docx_file)
    print(f"[+] Found {len(urls)} external hyperlinks and {len(direct_dois)} raw DOIs.\n")

    resolved_bibtex = {}
    resolved_dois = set(direct_dois)
    unresolved_urls = []

    # 1. Process explicit DOIs found in text
    for doi in direct_dois:
        print(f" -> Fetching BibTeX for DOI: {doi} ...", end=" ", flush=True)
        bib = fetch_bibtex_from_doi(doi, user_agent)
        if bib:
            m_key = re.search(r'@[a-zA-Z]+\{([^,]+),', bib)
            key = m_key.group(1) if m_key else doi
            resolved_bibtex[key] = bib
            print("DONE")
        else:
            print("FAILED (Crossref lookup failed)")

    # 2. Process URLs
    for url in urls:
        ident = resolve_url_to_identifier(url)
        itype = ident['type']
        ival = ident['id']

        if itype == 'doi':
            resolved_dois.add(ival)
            if ival in resolved_bibtex:
                continue
            print(f" -> Resolving DOI from URL [{ival}] ...", end=" ", flush=True)
            bib = fetch_bibtex_from_doi(ival, user_agent)
            if bib:
                m_key = re.search(r'@[a-zA-Z]+\{([^,]+),', bib)
                key = m_key.group(1) if m_key else ival
                resolved_bibtex[key] = bib
                print("DONE")
            else:
                fallback_bib = create_fallback_bibtex(url)
                resolved_bibtex[f"url_{len(resolved_bibtex)+1}"] = fallback_bib
                unresolved_urls.append(url)
                print("FALLBACK (@misc)")

        elif itype == 'pmid':
            print(f" -> Querying PubMed for PMID [{ival}] ...", end=" ", flush=True)
            bib, doi = fetch_metadata_from_pubmed(ival, user_agent)
            if bib:
                m_key = re.search(r'@[a-zA-Z]+\{([^,]+),', bib)
                key = m_key.group(1) if m_key else f"pmid_{ival}"
                resolved_bibtex[key] = bib
                if doi: resolved_dois.add(doi)
                print("DONE")
            else:
                fallback_bib = create_fallback_bibtex(url)
                resolved_bibtex[f"url_{len(resolved_bibtex)+1}"] = fallback_bib
                unresolved_urls.append(url)
                print("FALLBACK (@misc)")

        else:
            # Fallback web entry
            fallback_bib = create_fallback_bibtex(url)
            resolved_bibtex[f"url_{len(resolved_bibtex)+1}"] = fallback_bib
            unresolved_urls.append(url)
            if verbose:
                print(f" -> Added web fallback for: {url}")

        # Gentle throttle for public APIs
        time.sleep(0.1)

    # 3. Write BibTeX file
    with open(output_bib, 'w', encoding='utf-8') as f:
        f.write("% =========================================================\n")
        f.write(f"% BibTeX Library generated from {os.path.basename(docx_file)}\n")
        f.write(f"% Total Entries: {len(resolved_bibtex)}\n")
        f.write("% =========================================================\n\n")
        f.write('\n\n'.join(resolved_bibtex.values()))

    # 4. Write DOI list (for Zotero Magic Wand import)
    sorted_dois = sorted(list(resolved_dois))
    with open(output_dois, 'w', encoding='utf-8') as f:
        for d in sorted_dois:
            f.write(f"{d}\n")

    # 5. Write Citation Map (if requested)
    if output_map:
        with open(output_map, 'w', encoding='utf-8') as f:
            json.dump(citation_map, f, indent=2)

    print(f"\n=======================================================")
    print(f" EXTRACTION SUMMARY")
    print(f"=======================================================")
    print(f"[✓] Total References Extracted: {len(resolved_bibtex)}")
    print(f"[✓] Formal DOIs Identified:     {len(sorted_dois)}")
    print(f"[✓] Web Fallback Entries:       {len(unresolved_urls)}")
    print(f"\nOutputs saved:")
    print(f"  1. BibTeX Library: [ {output_bib} ] -> Ready to import into Zotero / Overleaf")
    print(f"  2. DOI List:       [ {output_dois} ] -> Can paste into Zotero 'Add by Identifier'")
    if output_map:
        print(f"  3. Citation Map:   [ {output_map} ] -> JSON mapping for LaTeX citation conversion")
    print(f"=======================================================\n")


# ==============================================================================
# CLI INTERFACE
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Extract hyperlinks from Word (.docx) documents and convert to Zotero-ready BibTeX library.",
        epilog="Example: python3 extract_docx_references.py manuscript.docx -o library.bib"
    )
    parser.add_argument("docx_file", help="Path to the input Word (.docx) document")
    parser.add_argument("-o", "--output-bib", default="references.bib", help="Output BibTeX file name (default: references.bib)")
    parser.add_argument("-d", "--dois", default="doi_list.txt", help="Output DOI list file name (default: doi_list.txt)")
    parser.add_argument("-m", "--map", help="Output citation map JSON (URL/DOI to citekey mapping)")
    parser.add_argument("-l", "--local-bib", nargs="*", help="Optional local .bib files for offline/cached metadata resolution")
    parser.add_argument("-e", "--email", help="Your email address (for polite Crossref/PubMed API rate limits)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print verbose output during execution")

    args = parser.parse_args()

    if not os.path.exists(args.docx_file):
        print(f"Error: Could not find file '{args.docx_file}'", file=sys.stderr)
        sys.exit(1)

    default_bibs = ["dissertation_references.bib"] if os.path.isfile("dissertation_references.bib") else []
    chosen_local = args.local_bib if args.local_bib is not None else default_bibs

    # Check if pipeline package is available
    try:
        from pipeline.reference_extractor import ReferenceExtractor
        extractor = ReferenceExtractor(
            user_agent=f"DocxReferenceExtractor/1.0 (mailto:{args.email})" if args.email else DEFAULT_USER_AGENT,
            local_bib_paths=chosen_local,
        )
        extractor.process(
            docx_file=args.docx_file,
            output_bib=args.output_bib,
            output_dois=args.dois,
            output_map=args.map,
            verbose=args.verbose,
        )
    except ImportError:
        process_docx_references(
            docx_file=args.docx_file,
            output_bib=args.output_bib,
            output_dois=args.dois,
            output_map=args.map,
            email=args.email,
            verbose=args.verbose
        )


if __name__ == "__main__":
    main()
