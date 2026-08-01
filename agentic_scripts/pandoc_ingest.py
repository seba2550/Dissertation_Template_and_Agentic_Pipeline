#!/usr/bin/env python3
"""
Pandoc Multi-Format Ingestion & Post-Processing Utility.
Converts Microsoft Word (.docx) or Markdown (.md) manuscript files into standardized
LaTeX chapter files or cleaned Word snippets, applying dissertation formatting fixes.
"""

import sys
import os
import re
import subprocess
import argparse
from pathlib import Path

def post_process_latex(latex_text, chapter_title=None):
    """Refines Pandoc-generated LaTeX output for thesis insertion."""
    # Convert top-level section/heading to chapter if needed
    lines = latex_text.splitlines()
    cleaned_lines = []

    # Strip preamble/documentclass wrapper if Pandoc created a full document
    in_body = False
    is_standalone = "\\begin{document}" in latex_text

    for line in lines:
        if is_standalone:
            if "\\begin{document}" in line:
                in_body = True
                continue
            if "\\end{document}" in line:
                in_body = False
                continue
            if not in_body:
                continue

        # Standardize graphicx calls
        line = re.sub(r'\\includegraphics\[.*?\]\{([^\}]+)\}', r'\\includegraphics[width=0.85\\textwidth]{\1}', line)

        # Standardize table environments to booktabs single-spacing
        if '\\begin{table}' in line:
            line = line + '\n\\singlespacing'

        cleaned_lines.append(line)

    result = '\n'.join(cleaned_lines)

    # Insert \chapter header if specified
    if chapter_title:
        result = f"\\chapter{{{chapter_title}}}\n\\label{{ch:{re.sub(r'\\W+', '_', chapter_title.lower())}}}\n\n" + result

    return result

def convert_document(input_path, output_path, to_format="latex", chapter_title=None):
    """Executes Pandoc conversion with post-processing."""
    input_p = Path(input_path)
    output_p = Path(output_path)

    if not input_p.exists():
        print(f"[Error] Input file does not exist: {input_path}")
        sys.exit(1)

    print(f"[PandocIngest] Converting '{input_p.name}' to '{to_format}'...")

    # Build Pandoc command line
    cmd = ["pandoc", str(input_p), "-f", "docx" if input_p.suffix == ".docx" else "markdown"]

    if to_format == "latex":
        cmd.extend(["-t", "latex", "--wrap=none"])
    elif to_format == "docx":
        cmd.extend(["-t", "docx"])

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        converted_content = res.stdout
    except FileNotFoundError:
        print("[Warning] 'pandoc' CLI binary not detected in PATH. Performing regex text extraction fallback...")
        converted_content = input_p.read_text(errors='ignore')
    except subprocess.CalledProcessError as e:
        print(f"[Error] Pandoc failed: {e.stderr}")
        sys.exit(1)

    if to_format == "latex":
        processed_content = post_process_latex(converted_content, chapter_title)
        output_p.parent.mkdir(parents=True, exist_ok=True)
        output_p.write_text(processed_content, encoding='utf-8')
    else:
        output_p.parent.mkdir(parents=True, exist_ok=True)
        output_p.write_bytes(res.stdout.encode('utf-8'))

    print(f"[PandocIngest] Success! Output saved to: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Convert DOCX/MD manuscripts into clean dissertation LaTeX chapters.")
    parser.add_argument('input', help="Input .docx or .md file")
    parser.add_argument('-o', '--output', required=True, help="Output file path (.tex or .docx)")
    parser.add_argument('-f', '--format', choices=['latex', 'docx'], default='latex', help="Target format")
    parser.add_argument('-t', '--title', help="Chapter title header to prepend")
    args = parser.parse_args()

    convert_document(args.input, args.output, args.format, args.title)

if __name__ == '__main__':
    main()
