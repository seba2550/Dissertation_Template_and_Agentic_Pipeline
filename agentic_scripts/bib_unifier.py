#!/usr/bin/env python3
"""
BibTeX Unifier and Clean-up Utility for Dissertation Compilation.
Parses multiple BibTeX files or citation files, deduplicates entries by DOI/Title,
strips redundant fields, standardizes entry keys, and generates a unified master .bib file.
"""

import sys
import os
import re
import argparse
from pathlib import Path

def parse_bib_entries(bib_content):
    """Simple robust BibTeX entry parser."""
    entries = []
    pattern = re.compile(r'@(\w+)\s*\{\s*([^,\s]+)\s*,', re.IGNORECASE)
    pos = 0
    while True:
        match = pattern.search(bib_content, pos)
        if not match:
            break
        entry_type = match.group(1).lower()
        cite_key = match.group(2)
        start_idx = match.start()
        
        # Track braces to find end of entry
        brace_count = 0
        end_idx = start_idx
        for i in range(match.end() - 1, len(bib_content)):
            char = bib_content[i]
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i + 1
                    break
        
        raw_entry = bib_content[start_idx:end_idx]
        pos = end_idx if end_idx > start_idx else match.end()
        
        # Extract DOI and Title for deduplication
        doi_match = re.search(r'doi\s*=\s*[\{"]([^"\}]+)[\}"]', raw_entry, re.IGNORECASE)
        title_match = re.search(r'title\s*=\s*[\{"]([^"\}]+)[\}"]', raw_entry, re.IGNORECASE)
        
        doi = doi_match.group(1).strip().lower() if doi_match else None
        title = re.sub(r'\s+', ' ', title_match.group(1)).strip().lower() if title_match else None
        
        entries.append({
            'type': entry_type,
            'key': cite_key,
            'doi': doi,
            'title': title,
            'raw': raw_entry
        })
    return entries

def clean_entry_fields(raw_entry):
    """Strips non-essential or messy fields from BibTeX entry."""
    lines = raw_entry.splitlines()
    cleaned_lines = []
    strip_fields = {'issn', 'isbn', 'urldate', 'language', 'note', 'eprint', 'file'}
    
    for line in lines:
        field_match = re.match(r'^\s*(\w+)\s*=', line)
        if field_match:
            field_name = field_match.group(1).lower()
            if field_name in strip_fields:
                continue
        cleaned_lines.append(line)
    return '\n'.join(cleaned_lines)

def unify_bib_files(input_files, output_file):
    """Combines and deduplicates BibTeX files."""
    seen_dois = set()
    seen_titles = set()
    seen_keys = set()
    unified_entries = []
    duplicates_count = 0

    print(f"[BibUnifier] Ingesting {len(input_files)} BibTeX file(s)...")

    for file_path in input_files:
        path = Path(file_path)
        if not path.exists():
            print(f"[Warning] File not found: {file_path}")
            continue
        
        content = path.read_text(encoding='utf-8', errors='ignore')
        entries = parse_bib_entries(content)
        print(f"  - {path.name}: Found {len(entries)} entries")

        for entry in entries:
            # Check duplicate by DOI
            if entry['doi'] and entry['doi'] in seen_dois:
                duplicates_count += 1
                continue
            # Check duplicate by Title
            if entry['title'] and entry['title'] in seen_titles:
                duplicates_count += 1
                continue
            
            # Ensure unique key
            key = entry['key']
            orig_key = key
            counter = 1
            while key in seen_keys:
                key = f"{orig_key}_{counter}"
                counter += 1
            
            if key != orig_key:
                entry_type = entry["type"]
                pattern_str = r'@(' + entry_type + r')\s*\{\s*' + re.escape(orig_key)
                replacement_prefix = f"@{entry_type}{{{key}"
                entry['raw'] = re.sub(pattern_str, replacement_prefix, entry['raw'], count=1)
                entry['key'] = key

            # Mark as seen
            if entry['doi']:
                seen_dois.add(entry['doi'])
            if entry['title']:
                seen_titles.add(entry['title'])
            seen_keys.add(key)

            cleaned_raw = clean_entry_fields(entry['raw'])
            unified_entries.append(cleaned_raw)

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text('\n\n'.join(unified_entries) + '\n', encoding='utf-8')

    print(f"\n[BibUnifier] Success! Output written to: {output_file}")
    print(f"  - Total Unique Entries: {len(unified_entries)}")
    print(f"  - Duplicates Removed: {duplicates_count}")

def main():
    parser = argparse.ArgumentParser(description="Unify and clean BibTeX reference files for dissertations.")
    parser.add_argument('inputs', nargs='+', help="Input .bib files")
    parser.add_argument('-o', '--output', default="unified_references.bib", help="Output .bib file path")
    args = parser.parse_args()
    
    unify_bib_files(args.inputs, args.output)

if __name__ == '__main__':
    main()
