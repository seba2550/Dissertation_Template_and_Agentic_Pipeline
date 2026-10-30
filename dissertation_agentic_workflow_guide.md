# Dissertation Agentic Workflow & Compliance Guide 🚀

A comprehensive, step-by-step operational guide for PhD candidates and AI assistants orchestrating the dissertation authoring, reference management, compilation, and institutional rubric validation pipeline.

---

## 🎯 Architectural Philosophy

Doctoral dissertations often incorporate manuscripts originally prepared across disparate word processors, co-authors, and journal formats. This pipeline establishes an automated, deterministic bridge between Microsoft Word drafts (`.docx`) and an institutionally certified LaTeX dissertation project compliant with all 26 rules of the **UCSF Dissertation Rubric (Rev 04/24)**.

---

## 🔄 The 6-Stage Lifecycle

```
[DOCX Manuscript]
       │
       ▼
[Stage 1: Reference & DOI Extraction] ──► (references.bib, doi_list.txt, citation_map.json)
       │
       ▼
[Stage 2: DOCX to LaTeX Conversion]   ──► (chX_chapter.tex with \cite{} keys)
       │
       ▼
[Stage 3: Template Integration]       ──► (dissertation_master.tex)
       │
       ▼
[Stage 4: Multi-Pass Compilation]     ──► (dissertation_master.pdf + .log)
       │
       ▼
[Stage 5: 26-Rule Rubric Audit]       ──► (audit_report.json + summary table)
       │
       ▼
[Stage 6: ProQuest ETD Archival]      ──► (Final certified PDF submission)
```

---

## 🛠 Stage-by-Stage Instructions

### Stage 1: Reference Extraction from DOCX Drafts

Word manuscripts frequently contain citations as plain text `[1, 2]`, embedded hyperlinks to publisher websites, or EndNote/Zotero bookmarks.

Run the reference extractor:
```bash
python3 run_pipeline.py extract-refs "Chapter_Draft.docx" \
  -o "ch_refs.bib" \
  -d "ch_dois.txt" \
  -m "citation_map.json" \
  -l "dissertation_references.bib"
```

**Key Behaviors**:
- **Offline Cache Priority**: If an existing master `.bib` file is provided via `-l/--local-bib`, the extractor queries local entries first, avoiding redundant network API calls.
- **Identifier Resolution**: Unpacks embedded relationships and converts URLs from Nature, Science, Springer, Cell Press, PMC, and bioRxiv into clean DOIs/PMIDs.
- **Citation Map**: Creates `citation_map.json`, mapping raw URLs and citation markers (e.g. `rId4` or DOI URLs) directly to BibTeX keys (e.g. `Horvath2013`).

---

### Stage 2: DOCX to LaTeX Conversion

Convert the narrative text from Word to modular LaTeX chapters while substituting citations:
```bash
python3 run_pipeline.py convert-docx "Chapter_Draft.docx" \
  -o "ch1_intro.tex" \
  -m "citation_map.json" \
  -t "Introduction and Background" \
  --label "ch:introduction"
```

**What the converter enforces**:
- Replaces raw web links with proper `\cite{citekey}` commands from `citation_map.json`.
- Restructures Word heading styles (`Heading 1`, `Heading 2`, etc.) into LaTeX `\section{...}`, `\subsection{...}`, and `\subsubsection{...}` in accordance with the institutional 4-level hierarchy.
- Strips non-standard Word characters and sanitizes LaTeX special characters (`%`, `&`, `_`, `#`).

---

### Stage 3: Master Document Configuration

Ensure the master document (`dissertation_master.tex` or `templates/latex/dissertation_master_template.tex`) contains the required preamble specifications:

```latex
\documentclass[12pt,oneside]{report}
\usepackage[letterpaper, top=1in, bottom=1in, left=1in, right=1in]{geometry}
\usepackage{mathptmx}
\usepackage{setspace}
\doublespacing

% Footskip >= 0.5 inches from paper edge
\setlength{\footskip}{0.6in}

% Captions: Tables above, Figures below (single-spaced, bold labels)
\usepackage[labelfont=bf, textfont=normalfont, singlelinecheck=off, font={small,singlespacing}]{caption}
\captionsetup[table]{position=above, skip=6pt, font={small,singlespacing}}
\captionsetup[figure]{position=below, skip=6pt, font={small,singlespacing}}

% Block quotations: single-spaced and indented
\usepackage{etoolbox}
\AtBeginEnvironment{quotation}{\singlespacing}
\AtBeginEnvironment{quote}{\singlespacing}

% Component headings in ALL CAPITAL LETTERS
\renewcommand{\contentsname}{TABLE OF CONTENTS}
\renewcommand{\listfigurename}{LIST OF FIGURES}
\renewcommand{\listtablename}{LIST OF TABLES}
```

---

### Stage 4: Multi-Pass Compilation

Compile the complete dissertation via `latexmk` or multi-pass `pdflatex` + `biber`:
```bash
python3 run_pipeline.py build -t dissertation_master.tex --validate
```

The build runner checks exit codes, counts total PDF pages, inspects log files, and automatically runs the rubric audit.

---

### Stage 5: Programmatic 26-Rule Rubric Audit

Audit the project against the full institutional rubric:
```bash
python3 run_pipeline.py validate-rubric -t dissertation_master.tex -j audit_report.json
```

Or using the standalone script:
```bash
python3 agentic_scripts/format_validator.py dissertation_master.tex
```

#### Diagnostic Remediation Checklist:
- **Title Abbreviations**: If `I.C_TITLE_ABBREVIATIONS` fails, expand all acronyms (e.g., *Alzheimer's Disease* instead of *AD*, *Single Nucleotide Polymorphisms* instead of *SNPs*).
- **Abstract Formatting**: Verify that the abstract is directly before the TOC, double-spaced, contains title and student name in ALL CAPS, and does **not** list committee members.
- **Copyright Page**: Confirm page `ii` contains `Copyright 20XX` followed by `by` (lowercase), your full name, and `ALL RIGHTS RESERVED`. Do **not** use the `©` symbol.
- **Publishing Agreement**: Confirm `\includepdf[pages={1}, pagecommand={\thispagestyle{fancy}}]{publishing_agreement.pdf}` is the last page, numbered, and not listed in the TOC.
- **Table / Figure Captions**: Confirm table captions are positioned **above** the table and figure captions are positioned **below** the figure.

---

### Stage 6: ProQuest ETD Submission Checklist

Before final upload to ProQuest ETD:
1. Verify degree conferral date matches the last month of your graduation term and year.
2. Confirm both a UCSF email and a permanent personal email are entered in ProQuest.
3. Confirm committee members match your official Advance to Candidacy petition on file.
4. Verify all fonts are embedded and the PDF has no password protection or security restrictions (`IV.D_PDF_SPEC`).

---

## 🧪 Continuous Integration & Testing

Run the test suite at any point to verify pipeline integrity:
```bash
python3 -m unittest discover tests -v
```
All 30 unit and integration tests must report `OK`.
