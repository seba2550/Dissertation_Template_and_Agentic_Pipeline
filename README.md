# Dissertation Template & Agentic Pipeline 🎓

A modular, zero-dependency agentic pipeline and LaTeX template framework designed to streamline the compilation, reference extraction, and institutional rubric validation of scientific doctoral dissertations (fully compliant with the **UCSF Dissertation Rubric Rev 04/24**).

> **New here, or not a programmer?** Start with the step-by-step **[TUTORIAL.md](TUTORIAL.md)**. It takes you from Word chapters to a checked, UCSF-ready PDF without any LaTeX knowledge.

---

## 🌟 Key Capabilities

1. **DOCX Reference & DOI Extractor**:
   - Deeply parses Microsoft Word (`.docx`) documents (including embedded Word hyperlinks, relationship XMLs, footnotes, endnotes, and raw text).
   - Resolves publication metadata via local BibTeX caches or live academic APIs (**Crossref**, **NCBI PubMed**, **PubMed Central**).
   - Outputs clean, Zotero-ready BibTeX files (`.bib`), DOI identifier lists (`.txt`), and citation mappings (`citation_map.json`).
   - **Zero external pip dependencies**: runs entirely on the Python 3.7+ standard library.

2. **Automated DOCX-to-LaTeX Conversion**:
   - Converts Word manuscripts into LaTeX chapter subfiles.
   - Remaps raw web hyperlinks and numerical citations into standardized `\cite{...}` keys.
   - Automatically structures section headings to conform with institutional hierarchy.

3. **Complete 26-Rule Rubric Verification Suite**:
   - Programmatically audits LaTeX master documents, preambles, body environments, chapter subfiles, and compilation logs against the complete **UCSF Dissertation Rubric**.
   - Validates font selection (12pt Times New Roman), 1-inch margins, footer clearance ($\ge 0.5$ in), title abbreviations, double spacing, lowercase Roman preliminary pagination, Arabic body pagination, chapter-based numbering (no letter suffixes), numeric square bracket citations, copyright page formatting (no $\copyright$ symbol), all-caps TOC/LOF/LOT headings, small single-spaced captions (tables above, figures below), single-spaced blockquotes via `etoolbox`, abstract formatting, and numbered publishing agreement.
   - Produces formatted console tables and machine-readable JSON reports.

4. **Automated LaTeX Compilation Manager**:
   - Executes multi-pass compilation (`latexmk` or `pdflatex` + `biber`).
   - Captures overfull boxes, undefined citations, and undefined cross-references.

---

## 📁 Repository Structure

```
├── agentic_scripts/
│   ├── bib_unifier.py                  # Merge & deduplicate multiple .bib files
│   ├── pandoc_ingest.py                # Alternative Pandoc-based DOCX/Markdown ingestion
│   └── setup_synthetic_test.py         # Regenerates the synthetic_test_run/ example
├── pipeline/
│   ├── __init__.py                     # Modular package exports
│   ├── cli.py                          # Unified CLI entrypoint
│   ├── reference_extractor.py          # DOCX hyperlink & reference extraction engine
│   ├── docx_converter.py               # DOCX to LaTeX conversion engine
│   ├── rubric_validator.py             # 26-rule institutional rubric validator
│   ├── compiler.py                     # LaTeX multi-pass build manager
│   └── utils.py                        # Identifier cleaners & BibTeX parser utilities
├── templates/
│   └── latex/
│       ├── dissertation_master_template.tex  # Master LaTeX template (all 26 rubric rules baked in)
│       ├── dissertation_master_template.pdf  # Compiled preview of the template
│       ├── ch1_intro.tex                     # Starter chapter with rubric-compliant headings/tables/figures
│       ├── references.bib                    # Starter bibliography
│       └── Title_Page / publishing_agreement # Front-matter .tex sources and the PDFs the master includes
├── synthetic_test_run/                 # Worked example: synthetic chapters run through the whole pipeline
├── rubric/                             # UCSF Dissertation Rubric (Rev 04/24), original + plain text
├── tests/
│   ├── __init__.py
│   ├── test_helpers.py                 # Shared fixtures (generates sample .docx files)
│   ├── test_reference_extractor.py     # Unit tests for URL/DOI resolution & extraction
│   ├── test_docx_converter.py          # Unit tests for DOCX parsing & citation mapping
│   ├── test_rubric_validator.py        # Unit tests covering all 26 rubric rules & edge cases
│   ├── test_pipeline_integration.py    # End-to-end integration & CLI tests
│   └── test_review_regressions.py      # Regression tests for fixed bugs
├── run_pipeline.py                     # Top-level CLI driver
├── dissertation_agentic_workflow_guide.md # Comprehensive agentic workflow guide
├── TUTORIAL.md                         # Step-by-step guide for non-programmers
├── LICENSE
└── README.md
```

---

## 🚀 Quick Start

### 1. Unified Pipeline CLI (`run_pipeline.py`)

The pipeline provides a consolidated command-line interface for all tasks:

```bash
# 1. Extract references and DOIs from a Word manuscript
python3 run_pipeline.py extract-refs manuscript.docx -o references.bib -d dois.txt -m citation_map.json
#    Tip: add -e you@institution.edu so Crossref/PubMed can contact you and give
#    your requests "polite pool" priority. Without it, requests are anonymous.

# 2. Convert Word manuscript to LaTeX chapter using citation map
python3 run_pipeline.py convert-docx manuscript.docx -o ch1_intro.tex -m citation_map.json

# 3. Compile dissertation PDF
python3 run_pipeline.py build -t dissertation_master.tex

# 4. Audit dissertation against all 26 rubric rules
python3 run_pipeline.py validate-rubric -t dissertation_master.tex -j rubric_report.json

# 5. Execute full end-to-end pipeline (extract -> convert -> compile -> validate)
python3 run_pipeline.py full-pipeline --docx manuscript.docx -o ch1_intro.tex -t dissertation_master.tex
```

---

### 2. Helper Scripts (`agentic_scripts/`)

```bash
# Merge several .bib files into one, removing duplicates by DOI/title
python3 agentic_scripts/bib_unifier.py a.bib b.bib -o unified_references.bib

# Alternative DOCX/Markdown -> LaTeX conversion via Pandoc (requires pandoc)
python3 agentic_scripts/pandoc_ingest.py --help
```

---

## 📋 Complete 26-Rule Rubric Audit Specification

The validator programmatically checks every requirement specified in the **UCSF Dissertation Rubric (Rev 04/24)**:

| # | Section | Rule ID | Audit Description | Requirement |
|---|---|---|---|---|
| 1 | I. General | `I.A_FONT` | Font Selection & Base Size | 12pt Times New Roman (`mathptmx`), Arial, or Garamond |
| 2 | I. General | `I.B_MARGINS` | Margin Specifications | Strict 1.0-inch margins on all sides (top, bottom, left, right) |
| 3 | I. General | `I.B.2_PAGENUM_POS` | Page Number Distance | Footer distance $\ge 0.5$ in from paper edge (`\footskip >= 0.6in`) |
| 4 | I. General | `I.C_TITLE_ABBREVIATIONS` | Title Spellings | Zero forbidden acronyms/abbreviations in dissertation title |
| 5 | I. General | `I.F_SPACING` | Manuscript Line Spacing | Double spacing throughout body and prelims via `setspace` |
| 6 | I. General | `I.G_TITLE_PAGE` | Title Page Setup | First page, unnumbered, counted as page i (`\setcounter{page}{2}`) |
| 7 | I. General | `I.H_PAGINATION` | Dual Pagination Schemes | Lower Roman (`ii, iii`) for prelims; Arabic (`1, 2`) for body |
| 8 | I. General | `I.H_NUMBERING_SCHEME` | Chapter Numbering | Chapter-based numbering (`1.1, 2.1`); no letter suffixes (`21a`) |
| 9 | I. General | `I.H_CITATION_BRACKETS`| Citation Format | Consistent numeric square brackets `[1]`; no subscripts |
| 10 | I. General | `I.I_COPYRIGHT` | Copyright Page (Page ii) | `Copyright 20XX / by / Name / ALL RIGHTS RESERVED` (no $\copyright$) |
| 11 | I. General | `I.J_PUBLISHING_AGREEMENT`| Publishing Agreement | Numbered final page via `pagecommand`; omitted from TOC |
| 12 | I. General | `I.K_LAYOUT` | Orientation & Paper | Standard portrait US Letter (8.5x11 in), single column |
| 13 | I. General | `I.L_WIDOWS_ORPHANS` | Widow & Orphan Penalties | `\clubpenalty=10000`, `\widowpenalty=10000` enforced |
| 14 | I. General | `I.N_ABSTRACT_PLACEMENT`| Abstract Configuration | Directly before TOC, double spaced, ALL CAPS heading/name/title |
| 15 | I. General | `I.P_ABBREVIATIONS` | List of Abbreviations | Required alphabetical list if abbreviations appear in manuscript |
| 16 | I. General | `I.DEOQ_PROQUEST_CHECKLIST`| ProQuest Guidelines | Candidacy committee, keywords, graduation term date, dual emails |
| 17 | II. Organization| `II.A_SEQUENTIAL_ORDER` | Sequential Component Order | Strict sequence from Title Page through Publishing Agreement |
| 18 | III. Headings | `III.J_HEADINGS` | Heading Hierarchy | Primary ALL CAPS centered, Secondary bold left, Tertiary italic |
| 19 | III. Tables | `III.A_TABLE_CAPTIONS` | Table Captions | Placed ABOVE table, small font, single spaced, bold table reference |
| 20 | III. Figures | `III.B_FIGURE_CAPTIONS` | Figure Captions | Placed BELOW figure, small font, single spaced |
| 21 | III. Quotations| `III.C_QUOTATIONS` | Block Quotations | Single-spaced, indented 5 spaces via `etoolbox` |
| 22 | III. TOC | `III.E_TOC_CLEANLINESS` | Table of Contents | ALL CAPS centered heading, excludes prelims & publishing agreement |
| 23 | III. Lists | `III.FG_LOF_LOT_SEPARATE`| Lists of Figures & Tables | Separate pages with ALL CAPS centered headings |
| 24 | IV. References| `IV.B_REFERENCES` | References Formatting | Titled "REFERENCES" (all caps), double spaced, listed in TOC |
| 25 | IV. Publishing| `IV.D_PDF_SPEC` | Electronic PDF Specs | Unencrypted, no password restrictions, printable |
| 26 | Compilation | `COMP_LOG_HEALTH` | Compilation Health | Zero undefined citations, zero undefined labels, zero fatal errors |

---

## 🧪 Running the Test Suite

The repository includes a comprehensive test suite with zero external dependencies:

```bash
# Run all unit and integration tests
python3 -m unittest discover tests -v
```

The suite verifies:
- Local and remote DOI/PMID/URL resolution.
- Embedded Word relationship parsing and footnote extraction.
- DOCX-to-LaTeX conversion with live citation dictionary remapping.
- Every individual rubric check with positive and negative test cases.
- Pre-compilation and post-compilation health checks.

Tests that compile LaTeX need a TeX distribution with `latexmk` (or `pdflatex`) and `biber`. Tests that build
or extract work in temporary directories and never modify files in `templates/`.

To regenerate the synthetic example in `synthetic_test_run/`:

```bash
python3 agentic_scripts/setup_synthetic_test.py --run-pipeline
```

---

## 📄 License & Attribution

Developed for academic dissertation authoring and computational biology workflows. Free and open source under the [MIT License](LICENSE).
