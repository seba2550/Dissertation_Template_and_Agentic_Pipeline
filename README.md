# Dissertation Template & Agentic AI Unification Pipeline

[![LaTeX Compliance](https://img.shields.io/badge/LaTeX-UCSF%20%2F%20ProQuest-blue.svg)](https://www.ucsf.edu)
[![MS Word Compliance](https://img.shields.io/badge/MS%20Word-Rubric%20Validated-green.svg)](https://www.ucsf.edu)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A complete framework, template suite, and agentic AI automation pipeline designed to format academic dissertations according to institutional guidelines (UCSF Graduate Division & ProQuest ETD) and unite disparate research manuscript formats (`.docx`, `.tex`, `.bib`, `.md`, supplementary tables/figures).

---

## 📌 Repository Overview

```
├── README.md                                # Repository landing page
├── dissertation_agentic_workflow_guide.md   # Master tutorial & agentic prompt guide
├── templates/
│   ├── latex/                               # Production-ready LaTeX master template
│   │   ├── dissertation_master_template.tex
│   │   ├── titlepage_template.tex
│   │   ├── ch1_template.tex
│   │   ├── ch2_template.tex
│   │   └── references.bib
│   └── word/
│       └── dissertation_word_guide.md       # Complete MS Word style & field guide
├── agentic_scripts/
│   ├── bib_unifier.py                       # BibTeX deduplication & cleaning utility
│   ├── pandoc_ingest.py                     # Multi-format DOCX/MD ingestion wrapper
│   └── format_validator.py                  # Static rubric compliance validator (LaTeX & DOCX)
└── rubric/
    ├── UCSF_Dissertation_Rubric_Rev_0424.docx # Official institutional benchmark rubric
    └── rubric_full.txt
```

---

## 🚀 Quick Start

### 1. Validate Your Dissertation File
Run the compliance validator on either a LaTeX master file or a Microsoft Word document:

```bash
# Validate LaTeX Master
python3 agentic_scripts/format_validator.py --tex templates/latex/dissertation_master_template.tex

# Validate Microsoft Word Document against UCSF Rubric
python3 agentic_scripts/format_validator.py --docx "path/to/my_dissertation.docx" --rubric rubric/rubric_full.txt
```

### 2. Unify and Clean BibTeX References
Merge multiple `.bib` files across chapters into a single deduplicated library:

```bash
python3 agentic_scripts/bib_unifier.py chapter1.bib chapter2.bib -o templates/latex/references.bib
```

### 3. Ingest Manuscripts into LaTeX Chapters
Convert `.docx` or `.md` manuscript drafts into clean LaTeX chapter files:

```bash
python3 agentic_scripts/pandoc_ingest.py draft_manuscript.docx -o templates/latex/ch3_template.tex -f latex --title "Epigenetic Clock Analysis"
```

---

## 📖 Complete Tutorial & Prompt Engineering Guide

For full documentation on UCSF/ProQuest formatting rules (margins, fonts, pagination, title page unlinking) and Agentic AI system prompts for LLM pair-programming, see:

📄 **[Dissertation Agentic Workflow Guide](dissertation_agentic_workflow_guide.md)**

---

## 📜 License
MIT License. Free to use and adapt for academic dissertations.
