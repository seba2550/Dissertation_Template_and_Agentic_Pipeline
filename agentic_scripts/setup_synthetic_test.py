#!/usr/bin/env python3
"""
agentic_scripts/setup_synthetic_test.py
======================================
Generates a complete synthetic test environment for testing the Dissertation
Template and Agentic Pipeline under realistic real-world conditions.

Creates:
1. synthetic_test_run/ directory
2. synthetic_chapter1_epigenetics.docx (with OpenXML styles, relationships, DOIs, PMIDs, BioRxiv, blockquotes)
3. synthetic_chapter2_meqtl.docx (with OpenXML styles, relationships, DOIs, PubMed, blockquotes)
4. local_cache.bib (local BibTeX cache with full bibliographic metadata for offline extraction)
5. Title_Page.pdf and publishing_agreement.pdf (copied from templates)
6. synthetic_master.tex (master dissertation LaTeX template compliant with UCSF Rubric Rev 04/24)
"""

import os
import sys
import shutil
import zipfile
import xml.sax.saxutils as saxutils

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
SYNTHETIC_DIR = os.path.join(BASE_DIR, "synthetic_test_run")
TEMPLATES_LATEX_DIR = os.path.join(BASE_DIR, "templates", "latex")


def build_docx(
    file_path: str,
    title: str,
    relationships: list,  # list of (rId, target_url)
    paragraphs: list,     # list of dicts: {'style': ..., 'runs': [{'text': ..., 'bold': ..., 'italic': ..., 'rId': ...}]}
):
    """Programmatically constructs a valid OpenXML .docx file."""
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

    pkg_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

    # Build word/_rels/document.xml.rels
    doc_rel_entries = []
    for r_id, target in relationships:
        doc_rel_entries.append(
            f'<Relationship Id="{r_id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="{target}" TargetMode="External"/>'
        )
    doc_rels = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  {''.join(doc_rel_entries)}
</Relationships>"""

    # Build word/document.xml
    body_xml_parts = []

    # Title paragraph
    body_xml_parts.append(f"""
    <w:p>
      <w:pPr><w:pStyle w:val="Heading1"/></w:pPr>
      <w:r><w:t>{saxutils.escape(title)}</w:t></w:r>
    </w:p>""")

    for p in paragraphs:
        if p.get('table'):
            tbl_rows = p['table'].get('rows', [])
            tbl_xml = ["<w:tbl>"]
            for r in tbl_rows:
                tbl_xml.append("<w:tr>")
                for cell in r:
                    tbl_xml.append(f"<w:tc><w:p><w:r><w:t>{saxutils.escape(str(cell))}</w:t></w:r></w:p></w:tc>")
                tbl_xml.append("</w:tr>")
            tbl_xml.append("</w:tbl>")
            body_xml_parts.append("".join(tbl_xml))
            continue

        style = p.get('style', '')
        style_xml = f'<w:pStyle w:val="{style}"/>' if style else ''
        pPr_xml = f'<w:pPr>{style_xml}</w:pPr>' if style_xml else ''

        runs_xml = []
        for r in p.get('runs', []):
            raw_text = r.get('text', '')
            text = saxutils.escape(raw_text)
            bold = r.get('bold', False)
            italic = r.get('italic', False)
            r_id = r.get('rId')

            rPr_parts = []
            if bold:
                rPr_parts.append('<w:b/>')
            if italic:
                rPr_parts.append('<w:i/>')
            rPr_xml = f"<w:rPr>{''.join(rPr_parts)}</w:rPr>" if rPr_parts else ""

            run_str = f"<w:r>{rPr_xml}<w:t xml:space=\"preserve\">{text}</w:t></w:r>"
            if r_id:
                run_str = f'<w:hyperlink r:id="{r_id}">{run_str}</w:hyperlink>'
            runs_xml.append(run_str)

        body_xml_parts.append(f"""
    <w:p>
      {pPr_xml}
      {''.join(runs_xml)}
    </w:p>""")

    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:body>
    {''.join(body_xml_parts)}
  </w:body>
</w:document>"""

    with zipfile.ZipFile(file_path, 'w') as z:
        z.writestr('[Content_Types].xml', content_types)
        z.writestr('_rels/.rels', pkg_rels)
        z.writestr('word/_rels/document.xml.rels', doc_rels)
        z.writestr('word/document.xml', document_xml)


def generate_local_cache_bib(path: str):
    """Creates a comprehensive local BibTeX cache containing verified metadata."""
    bib_content = """% Local BibTeX Cache for Synthetic Test Run

@article{Horvath2013,
  author = {Horvath, Steve},
  title = {DNA methylation age of human tissues and cell types},
  journal = {Genome Biology},
  year = {2013},
  volume = {14},
  number = {10},
  pages = {3156},
  doi = {10.1186/gb-2013-14-10-r115}
}

@article{Hannum2013,
  author = {Hannum, Gregory and Guinney, Justin and Zhao, Ling and Zhang, Li and Hughes, Guy and Sadda, SriniVas and Klotzle, Brandy and Bibikova, Marina and Fan, Jian-Bing and Gao, Yuan and Deconde, Rob and Chen, Ming and Rajapakse, Indika and Friend, Stephen and Ideker, Trey and Kang, Kang},
  title = {Genome-wide Methylation Profiles Reveal Quantitative Views of Human Aging Rates},
  journal = {Molecular Cell},
  year = {2013},
  volume = {49},
  number = {2},
  pages = {359--367},
  doi = {10.1016/j.molcel.2012.10.016}
}

@article{Levine2018,
  author = {Levine, Morgan E. and Lu, Ake T. and Quach, Austin and Chen, Brian H. and Assimes, Themistocles L. and Bandinelli, Stefania and Hou, Lifang and Baccarelli, Andrea A. and Stewart, James D. and Li, Yun and Whitsel, Eric A. and Wilson, James G. and Reiner, Alex P. and Aviv, Abraham and Lohman, Kurt and Liu, Yongmei and Ferrucci, Luigi and Horvath, Steve},
  title = {An epigenetic biomarker of aging for lifespan and healthspan},
  journal = {Aging (Albany NY)},
  year = {2018},
  volume = {10},
  number = {4},
  pages = {573--591},
  doi = {10.18632/aging.101414}
}

@article{Lu2019,
  author = {Lu, Ake T. and Quach, Austin and Wilson, James G. and Reiner, Alex P. and Aviv, Abraham and Raj, Kenneth and Hou, Lifang and Baccarelli, Andrea A. and Li, Yun and Stewart, James D. and Whitsel, Eric A. and Assimes, Themistocles L. and Ferrucci, Luigi and Horvath, Steve},
  title = {DNA methylation GrimAge strongly predicts lifespan and healthspan},
  journal = {Aging (Albany NY)},
  year = {2019},
  volume = {11},
  number = {2},
  pages = {303--327},
  doi = {10.18632/aging.101684}
}

@article{Smith2024,
  author = {Smith, Jane A. and Taylor, Robert M. and Johnson, Emily K. and Williams, Sarah L.},
  title = {Cross-ancestry transferability and genetic fine-mapping of molecular aging clocks},
  journal = {Nature},
  year = {2024},
  volume = {628},
  number = {8007},
  pages = {412--420},
  doi = {10.1038/nature12345}
}

@article{Cell2020,
  author = {Gopalan, Shyamalika and Carja, Oana and Fagny, Maud and Patin, Etienne and Quintana-Murci, Lluis and Henn, Brenna M.},
  title = {Trends in DNA Methylation with Age in Diverse Human Populations},
  journal = {Cell},
  year = {2020},
  volume = {180},
  number = {1},
  pages = {97--111},
  doi = {10.1016/j.cell.2020.01.001}
}

@article{Pubmed2024,
  author = {Chen, Wei and Zhang, Yu and Davis, Michael},
  title = {Robust deep learning architectures for biological age estimation from multi-ancestry epigenomes},
  journal = {Bioinformatics},
  year = {2024},
  volume = {40},
  number = {1},
  pages = {btad777},
  pmid = {38196633},
  doi = {10.1093/bioinformatics/btad777}
}

@article{Biorxiv2023,
  author = {Cruz-González, Sebastián and Capra, John A.},
  title = {Systematic evaluation of population stratification in DNA methylation aging clocks},
  journal = {bioRxiv},
  year = {2023},
  doi = {10.1101/2023.01.01.123456}
}
"""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(bib_content.strip() + "\n")


def generate_synthetic_documents():
    """Generates synthetic manuscripts for Chapter 1 and Chapter 2."""
    os.makedirs(SYNTHETIC_DIR, exist_ok=True)

    # 1. Chapter 1 Manuscript
    ch1_path = os.path.join(SYNTHETIC_DIR, "synthetic_chapter1_epigenetics.docx")
    ch1_rels = [
        ("rId1", "https://doi.org/10.1186/gb-2013-14-10-r115"),
        ("rId2", "https://doi.org/10.1016/j.molcel.2012.10.016"),
        ("rId3", "https://doi.org/10.18632/aging.101414"),
        ("rId4", "https://doi.org/10.18632/aging.101684"),
        ("rId5", "https://doi.org/10.1038/nature12345"),
        ("rId6", "https://pubmed.ncbi.nlm.nih.gov/38196633/"),
        ("rId7", "https://www.biorxiv.org/content/10.1101/2023.01.01.123456v1"),
    ]
    ch1_paras = [
        # Heading 1
        {"style": "Heading1", "runs": [{"text": "Epigenetic Clocks and Biological Aging Dynamics"}]},
        # Section 1
        {
            "runs": [
                {"text": "Biological aging is characterized by systematic molecular remodeling across the epigenome. The pioneer pan-tissue clock developed by Horvath "},
                {"text": "[1]", "rId": "rId1"},
                {"text": " demonstrated that DNA methylation status at 353 CpG dinucleotides accurately tracks chronological age across diverse human tissues. Similarly, Hannum and colleagues "},
                {"text": "[2]", "rId": "rId2"},
                {"text": " identified a blood-specific methylation predictor consisting of 71 markers that captured clinical markers of physiological decline."},
            ]
        },
        # Subsection
        {"style": "Heading2", "runs": [{"text": "Second-Generation Clocks and Mortality Prediction"}]},
        {
            "runs": [
                {"text": "Subsequent investigations introduced biomarkers trained on physiological phenotypes and mortality risks rather than purely chronological time. Specifically, PhenoAge "},
                {"text": "[3]", "rId": "rId3"},
                {"text": " and GrimAge "},
                {"text": "[4]", "rId": "rId4"},
                {"text": " demonstrated superior predictive validity for morbidity and all-cause mortality. However, recent cross-population benchmarks "},
                {"text": "[5]", "rId": "rId5"},
                {"text": " revealed notable calibration disparities when applied across ancestrally diverse cohorts. Furthermore, Gopalan et al. (10.1016/j.cell.2020.01.001) highlighted divergence in age-associated methylation dynamics between global populations."},
            ]
        },
        # Subsection with bold/italic and special characters
        {"style": "Heading2", "runs": [{"text": "Methodological Harmonization Across Cohorts"}]},
        {
            "runs": [
                {"text": "To address platform discrepancies, we evaluated quality control filters where "},
                {"text": "probe failure rates exceeded 15% & sample heterozygosity", "bold": True},
                {"text": " was systematically audited. In particular, "},
                {"text": "cross-reactive probes and non-specific hybridization", "italic": True},
                {"text": " were masked prior to regularized elastic net fitting."},
            ]
        },
        # Blockquote
        {
            "style": "Quote",
            "runs": [
                {"text": "Biological age acceleration represents the mathematical divergence between chronological time and physiological vitality. Epigenetic markers provide an empirical substrate to map this divergence across human lifespans, integrating genetic variation, environmental exposures, and social determinants into an actionable, quantitative metric of organismal resilience."}
            ]
        },
        # Caption & Table 1.1
        {"style": "Caption", "runs": [{"text": "Table 1.1: Multi-ancestry DNA methylation profiling cohorts and technology platforms."}]},
        {
            "table": {
                "rows": [
                    ["Cohort Name", "Ancestral Group", "Sample Size (N)", "Platform"],
                    ["Discovery Cohort", "Multi-Ancestry", "621", "EPIC BeadChip"],
                    ["Validation Cohort A", "African American", "1,394", "450K BeadChip"],
                    ["Validation Cohort B", "European", "729", "450K BeadChip"],
                ]
            }
        },
        # Subsection 3
        {"style": "Heading3", "runs": [{"text": "Deep Learning Implementations"}]},
        {
            "runs": [
                {"text": "Novel neural network architectures have shown promising accuracy for high-dimensional methylation modeling as described by Chen and colleagues "},
                {"text": "[6]", "rId": "rId6"},
                {"text": ". Preprints on population stratification further underscore this need "},
                {"text": "[7]", "rId": "rId7"},
                {"text": "."},
            ]
        },
        # Markdown-style heading
        {"runs": [{"text": "## Discussion and Future Perspectives"}]},
        {
            "runs": [
                {"text": "Our findings underscore the imperative of ancestry-inclusive training datasets to ensure equitable clinical utility of molecular aging biomarkers."}
            ]
        },
    ]

    build_docx(
        file_path=ch1_path,
        title="EPIGENETIC CLOCK PREDICTION PERFORMANCE ACROSS DIVERSE POPULATIONS",
        relationships=ch1_rels,
        paragraphs=ch1_paras,
    )

    # 2. Chapter 2 Manuscript
    ch2_path = os.path.join(SYNTHETIC_DIR, "synthetic_chapter2_meqtl.docx")
    ch2_rels = [
        ("rId1", "https://doi.org/10.1038/nature12345"),
        ("rId2", "https://doi.org/10.1186/gb-2013-14-10-r115"),
        ("rId3", "https://pubmed.ncbi.nlm.nih.gov/38196633/"),
    ]
    ch2_paras = [
        {"style": "Heading1", "runs": [{"text": "Genetic Architecture of Epigenetic Regulation"}]},
        {
            "runs": [
                {"text": "Genetic variants exert profound regulatory influences on local and distal DNA methylation levels. Previous comprehensive mapping initiatives "},
                {"text": "[1]", "rId": "rId1"},
                {"text": " demonstrated that methylation quantitative trait loci (meQTL) are enriched in disease-associated regions. Linking these variants to aging markers "},
                {"text": "[2]", "rId": "rId2"},
                {"text": " establishes mechanistic pathways connecting sequence variation to epigenetic age acceleration. Complementary approaches are discussed in 10.1016/j.cell.2020.01.001."},
            ]
        },
        {"style": "Heading2", "runs": [{"text": "Ancestry-Stratified Fine-Mapping Procedures"}]},
        {
            "runs": [
                {"text": "We implemented Bayesian fine-mapping algorithms to dissect causal variant credible sets across ancestrally distinct cohorts. Consistent with "},
                {"text": "[3]", "rId": "rId3"},
                {"text": ", trans-ancestry fine-mapping substantially narrowed the credible set sizes by exploiting differential linkage disequilibrium architecture."},
            ]
        },
        {
            "style": "Quote",
            "runs": [
                {"text": "Deciphering the causal interplay between sequence-level genetic variation and dynamic epigenetic modifications is foundational to interpreting GWAS discoveries and constructing biologically robust, multi-ancestry risk prediction models."}
            ]
        },
        {"style": "Heading2", "runs": [{"text": "Colocalization and Functional Validation"}]},
        {
            "runs": [
                {"text": "Colocalization analyses confirmed shared genetic etiology between meQTL and complex traits in over 42% of tested genomic loci."}
            ]
        },
    ]

    build_docx(
        file_path=ch2_path,
        title="MAPPING GENETIC ARCHITECTURE OF METHYLATION QUANTITATIVE TRAIT LOCI",
        relationships=ch2_rels,
        paragraphs=ch2_paras,
    )


def generate_synthetic_master_tex(path: str):
    """Generates the master dissertation LaTeX file for the synthetic test environment."""
    content = r"""\documentclass[12pt,oneside]{report}

%%% ========================================================================= %%%
%%% UCSF DISSERTATION MASTER LATEX TEMPLATE - SYNTHETIC TEST SUITE            %%%
%%% Fully compliant with UCSF Dissertation Rubric (Rev 04/24)                 %%%
%%% ========================================================================= %%%

%%% ------------ I. MARGINS, FONT & SPACING (RUBRIC SEC I.A, I.B, I.F) ------------ %%%
\usepackage[letterpaper, top=1in, bottom=1in, left=1in, right=1in]{geometry}
\usepackage{mathptmx} % Times New Roman 12pt TrueType font
\usepackage{microtype} % Protrusion and font expansion to prevent overfull hboxes
\usepackage{setspace}
\doublespacing % Double spacing throughout text

\usepackage{graphicx}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{booktabs}
\usepackage{multirow}
\usepackage{array}
\usepackage{pdfpages}
\usepackage[colorlinks=true, linkcolor=black, citecolor=black, urlcolor=black, breaklinks=true]{hyperref}
\usepackage[capitalise, noabbrev, nameinlink]{cleveref}

%%% ------------ CITATION FORMATTING (RUBRIC SEC I.H) ------------ %%%
\usepackage[
  sorting=none,
  backend=biber,
  style=numeric-comp,
  natbib=true,
  doi=true,
  url=false,
  isbn=false
]{biblatex}
\addbibresource{references.bib}

%%% ------------ WIDOWS & ORPHANS (RUBRIC SEC I.L) ------------ %%%
\clubpenalty=10000
\widowpenalty=10000
\displaywidowpenalty=10000

%%% ------------ HEADING HIERARCHY (RUBRIC SEC III.J) ------------ %%%
\usepackage{titlesec}

% Primary: All caps, bold, centered, double spaced above section
\titleformat{\chapter}[display]
  {\normalfont\bfseries\centering\LARGE}
  {\MakeUppercase{\chaptertitlename\ \thechapter}}
  {10pt}
  {\MakeUppercase}
\titlespacing*{\chapter}{0pt}{0pt}{30pt}

% Secondary: Sentence case, bold, left-aligned
\titleformat{\section}
  {\normalfont\bfseries\large\raggedright}
  {\thesection}
  {1em}
  {}
\titlespacing*{\section}{0pt}{18pt}{6pt}

% Tertiary: Sentence case, italic, left-aligned
\titleformat{\subsection}
  {\normalfont\itshape\large\raggedright}
  {\thesubsection}
  {1em}
  {}
\titlespacing*{\subsection}{0pt}{12pt}{4pt}

% Quaternary: Sentence case, italic, left-aligned, run-in with period
\titleformat{\subsubsection}[runin]
  {\normalfont\itshape}
  {\thesubsubsection}
  {1em}
  {}
  [.]
\titlespacing*{\subsubsection}{0pt}{6pt}{6pt}

%%% ------------ CAPTION FORMATTING (RUBRIC SEC III.A & III.B) ------------ %%%
\usepackage[labelfont=bf, textfont=normalfont, singlelinecheck=off, font={small,singlespacing}]{caption}
\captionsetup[table]{position=above, skip=6pt, font={small,singlespacing}}
\captionsetup[figure]{position=below, skip=6pt, font={small,singlespacing}}

%%% ------------ BLOCK QUOTATIONS (RUBRIC SEC I.F & III.C) ------------ %%%
\usepackage{etoolbox}
\AtBeginEnvironment{quotation}{\singlespacing}
\AtBeginEnvironment{quote}{\singlespacing}

%%% ------------ ALL CAPS COMPONENT HEADINGS (RUBRIC SEC III.E, III.F, III.G) ------------ %%%
\renewcommand{\contentsname}{TABLE OF CONTENTS}
\renewcommand{\listfigurename}{LIST OF FIGURES}
\renewcommand{\listtablename}{LIST OF TABLES}

%%% ------------ PAGINATION & FOOTER (RUBRIC SEC I.B.2 & I.H) ------------ %%%
\usepackage{fancyhdr}
\pagestyle{fancy}
\fancyhf{}
\cfoot{\thepage} % Bottom center pagination
\renewcommand{\headrulewidth}{0pt}
\setlength{\footskip}{0.6in} % Footer distance >= 0.5in from edge

\begin{document}

%%% ========================================================================= %%%
%%% PRELIMINARY PAGES (Numbered in lowercase Roman numerals)                   %%%
%%% ========================================================================= %%%
\pagenumbering{roman}

% --- TITLE PAGE (Page i, unnumbered, Rubric Sec I.G) ---
\includepdf[pages={1}]{Title_Page.pdf}
\setcounter{page}{2} % Copyright page is Page ii

% --- COPYRIGHT PAGE (Page ii, Rubric Sec I.I & III.B) ---
\thispagestyle{fancy}
\begin{center}
  \vspace*{2.5in}
  Copyright 2026\\[0.2in]
  by\\[0.2in]
  AUTHOR FULL NAME\\[0.2in]
  ALL RIGHTS RESERVED
\end{center}
\clearpage

% --- DEDICATION (Optional, Rubric Sec III.C) ---
\chapter*{DEDICATION}
\doublespacing
Dedicated to my family, mentors, and colleagues whose encouragement made this work possible.
\clearpage

% --- ACKNOWLEDGEMENTS (Optional, Rubric Sec III.C) ---
\chapter*{ACKNOWLEDGEMENTS}
\doublespacing
I express my deepest gratitude to my advisor, dissertation committee members, and collaborators.
\clearpage

% --- CONTRIBUTIONS (Optional, Rubric Sec III.C) ---
\chapter*{CONTRIBUTIONS}
\doublespacing
Descriptions of student and co-author contributions for adapted manuscript chapters.
\clearpage

% --- EPIGRAPH (Optional, Rubric Sec III.C) ---
\chapter*{EPIGRAPH}
\doublespacing
\vspace*{1.5in}
\begin{quotation}
  \itshape
  ``Equipped with his five senses, man explores the universe around him and calls the adventure Science.''
\end{quotation}
\begin{flushright}
  --- Edwin Powell Hubble (1948)
\end{flushright}
\clearpage

% --- ABSTRACT (Required, Rubric Sec I.N & III.D) ---
\chapter*{ABSTRACT}
\doublespacing
\begin{center}
  \textbf{COMPUTATIONAL EVALUATION OF EPIGENETIC CLOCKS AND TRANSCRIPTIONAL REGULATION ACROSS DIVERSE POPULATIONS}\\[0.08in]
  \textbf{AUTHOR FULL NAME}
\end{center}
\vspace{0.05in}

\noindent Epigenetic clocks provide a molecular readout of chronological and biological age. This dissertation investigates cross-ancestry prediction performance, fine-maps methylation quantitative trait loci, and establishes standardized computational workflows for equitable biomarker translation.
\clearpage

% --- TABLE OF CONTENTS (Required, Rubric Sec III.E) ---
\tableofcontents
\clearpage

% --- LIST OF FIGURES (Required if figures present, Rubric Sec III.G) ---
\listoffigures
\clearpage

% --- LIST OF TABLES (Required if tables present, Rubric Sec III.F) ---
\listoftables
\clearpage

% --- LIST OF ABBREVIATIONS (Required if abbreviations used, Rubric Sec I.P & III.H) ---
\chapter*{LIST OF ABBREVIATIONS}
\doublespacing
\begin{tabular}{lp{5in}}
  \textbf{CpG} & Cytosine-phosphate-Guanine dinucleotide \\
  \textbf{DNA} & Deoxyribonucleic Acid \\
  \textbf{GWAS} & Genome-Wide Association Study \\
  \textbf{meQTL} & Methylation Quantitative Trait Loci \\
  \textbf{SNP} & Single Nucleotide Polymorphism \\
  \textbf{UCSF} & University of California, San Francisco \\
\end{tabular}
\clearpage

%%% ========================================================================= %%%
%%% MAIN BODY (Numbered in Arabic numerals starting at 1, Rubric Sec I.H)     %%%
%%% ========================================================================= %%%
\pagenumbering{arabic}
\setcounter{page}{1}
\doublespacing

% Include Chapter 1 (contains converted sections, citations, blockquotes, and Table 1.1)
\input{ch1_epigenetics}
\clearpage

% Insert Figure 1.1 to satisfy List of Figures (Rubric Sec III.G)
\begin{figure}[htbp]
  \centering
  \rule{0.8\linewidth}{2in}
  \caption[Conceptual diagram of multi-ancestry clock evaluation and meQTL mapping.]{
    \textbf{Conceptual diagram of multi-ancestry clock evaluation and meQTL mapping.}
    High-throughput DNA methylation profiles are filtered, evaluated for biological age acceleration, and integrated with genotype arrays for ancestry-stratified fine-mapping.
  }
  \label{fig:method_overview}
\end{figure}
\clearpage

% Include Chapter 2
\input{ch2_meqtl}
\clearpage

%%% ========================================================================= %%%
%%% REFERENCES SECTION (Required, Rubric Sec IV.B)                            %%%
%%% ========================================================================= %%%
\printbibliography[heading=bibintoc, title={REFERENCES}]
\clearpage

%%% ========================================================================= %%%
%%% UCSF PUBLISHING AGREEMENT (Required, Rubric Sec I.J & IV.C)               %%%
%%% ========================================================================= %%%
\includepdf[pages={1}, pagecommand={\thispagestyle{fancy}}]{publishing_agreement.pdf}

\end{document}
"""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Synthetic Test Environment Generator")
    parser.add_argument("--run-pipeline", action="store_true", help="Automatically run full pipeline after generating test suite")
    args = parser.parse_args()

    print("[*] Generating synthetic test directory and fixtures...")
    os.makedirs(SYNTHETIC_DIR, exist_ok=True)

    # 1. Create synthetic manuscripts (.docx)
    print("    1. Building synthetic .docx manuscripts...")
    generate_synthetic_documents()

    # 2. Create local citation database (.bib)
    print("    2. Building local BibTeX reference cache...")
    local_cache_path = os.path.join(SYNTHETIC_DIR, "local_cache.bib")
    generate_local_cache_bib(local_cache_path)

    # 3. Copy title page and publishing agreement PDFs
    print("    3. Copying official PDF templates...")
    title_pdf_src = os.path.join(TEMPLATES_LATEX_DIR, "Title_Page.pdf")
    pub_pdf_src = os.path.join(TEMPLATES_LATEX_DIR, "publishing_agreement.pdf")
    shutil.copy2(title_pdf_src, os.path.join(SYNTHETIC_DIR, "Title_Page.pdf"))
    shutil.copy2(pub_pdf_src, os.path.join(SYNTHETIC_DIR, "publishing_agreement.pdf"))

    # 4. Create synthetic master dissertation LaTeX file
    print("    4. Writing synthetic master dissertation LaTeX file...")
    master_tex_path = os.path.join(SYNTHETIC_DIR, "synthetic_master.tex")
    generate_synthetic_master_tex(master_tex_path)

    print(f"[✓] Synthetic test environment successfully prepared in: {SYNTHETIC_DIR}")

    if args.run_pipeline:
        print("\n[*] Executing full pipeline on synthetic test environment...")
        from pipeline.cli import main as cli_main
        ch1_docx = os.path.join(SYNTHETIC_DIR, "synthetic_chapter1_epigenetics.docx")
        ch2_docx = os.path.join(SYNTHETIC_DIR, "synthetic_chapter2_meqtl.docx")
        ch1_tex = os.path.join(SYNTHETIC_DIR, "ch1_epigenetics.tex")
        ch2_tex = os.path.join(SYNTHETIC_DIR, "ch2_meqtl.tex")
        ref_bib = os.path.join(SYNTHETIC_DIR, "references.bib")
        cmap_json = os.path.join(SYNTHETIC_DIR, "citation_map.json")

        cmd = [
            "full-pipeline",
            "--docx", ch1_docx, ch2_docx,
            "-t", master_tex_path,
            "-o", ch1_tex, ch2_tex,
            "-b", ref_bib,
            "-m", cmap_json,
            "-l", local_cache_path,
        ]
        ret = cli_main(cmd)
        if ret != 0:
            print("[!] Pipeline execution failed.")
            return ret
        print("[✓] Full pipeline execution succeeded on synthetic test suite.")
        return 0


if __name__ == "__main__":
    main()
