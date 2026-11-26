# Dissertation Agentic Workflow & Compliance Guide 🚀

A comprehensive, step-by-step operational guide for PhD candidates and AI assistants orchestrating the dissertation authoring, reference management, compilation, and institutional rubric validation pipeline.

---

## 🎯 Architectural Philosophy

Doctoral dissertations often incorporate manuscripts originally prepared across disparate word processors, co-authors, and journal formats. This pipeline establishes an automated, deterministic bridge between Microsoft Word drafts (`.docx`) and an institutionally certified LaTeX dissertation project compliant with all 30 rules (rubric plus layout checks) of the **UCSF Dissertation Rubric (Rev 04/24)**.

---

## 🔄 The 6-Stage Lifecycle

```
[DOCX Manuscript]
       │
       ▼
[Stage 1: Reference & DOI Extraction] ──► (extracted_references.bib, doi_list.txt, citation_map.json)
       │
       ▼
[Stage 2: DOCX to LaTeX Conversion]   ──► (chX_chapter.tex with \cite{} keys)
       │
       ▼
[Stage 3: Template Integration]       ──► (dissertation_master.tex)
       │
       ▼
[Stage 4: Fonts + Compilation]        ──► (build_embedded/, dissertation_master.pdf + .log)
       │
       ▼
[Stage 4b: PDF Layout Audit]         ──► (layout_audit.py: 0 issue(s))
       │
       ▼
[Stage 5: 30-Rule Rubric Audit]       ──► (audit_report.json + summary table)
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
- **Never writes over your bibliography**: the default output is `extracted_references.bib`, and an output `.bib` that already has entries (or an existing chapter `.tex`) is refused unless you pass `--overwrite` (the old file is then backed up to `<name>.bak-<timestamp>`). An output that is also a `-l` cache file is always refused. Treat extracted entries as unverified: check them, then merge by hand.
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

% Page number >= 0.5in from the paper edge. \footskip is measured DOWN from the text block,
% so the number sits (bottom margin - footskip) above the edge: 1in - 0.42in = 0.58in.
\setlength{\footskip}{0.42in}

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

The template's preamble also carries the layout rules (float placement, short last lines, bold references, bibliography clean-up); copy the whole preamble rather than this excerpt.

---

### Stage 4: Fonts and Multi-Pass Compilation

R's `pdf()` device leaves Helvetica unembedded, and DocuSign title pages and agreements leave Arial unembedded (Rubric IV.D). Whenever a figure, the title page or the publishing agreement changes, write font-embedded copies first. The signed forms go after `--forms`: their text becomes vector outlines and their own tags are dropped, since DocuSign/Word fonts and tags fail ProQuest's accessibility check:
```bash
agentic_scripts/embed_fonts.sh figures/ --forms Title_Page.pdf publishing_agreement.pdf
```
Then compile the complete dissertation with LuaLaTeX + `biber` (`latexmk -lualatex`; never `-pdf`, which cannot build the tagged PDF):
```bash
python3 run_pipeline.py build -t dissertation_master.tex --validate
```

The build runner checks exit codes, counts total PDF pages, inspects log files, and automatically runs the rubric audit.

### Stage 4b: PDF Layout Audit

The rubric audit reads the `.tex`; only the compiled PDF shows where floats and paragraph ends actually landed:
```bash
python3 agentic_scripts/layout_audit.py dissertation_master.pdf
```
Expect `0 issue(s)`, then look at the pages it names (it works from extracted text). Fix a reported case per figure: resize it, or move the figure to the end of the subsection that cites it. Do not reintroduce `[p]` floats.

---

### Stage 5: Programmatic 30-Rule Rubric Audit

Audit the project against the full institutional rubric:
```bash
python3 run_pipeline.py validate-rubric -t dissertation_master.tex -j audit_report.json
```


#### Diagnostic Remediation Checklist:
- **Title Abbreviations**: If `I.C_TITLE_ABBREVIATIONS` fails, expand all acronyms (e.g., *Alzheimer's Disease* instead of *AD*, *Single Nucleotide Polymorphisms* instead of *SNPs*).
- **Abstract Formatting**: Verify that the abstract is directly before the TOC, double-spaced, contains title and student name in ALL CAPS, and does **not** list committee members.
- **Copyright Page**: Confirm page `ii` contains `Copyright 20XX` followed by `by` (lowercase), your full name, and `ALL RIGHTS RESERVED`. Do **not** use the `©` symbol.
- **Publishing Agreement**: Last page, numbered, not in the TOC. Set `\AgreementPageStyle` in the preamble: `{fancy}` if LaTeX should number it, `{empty}` if the signed DocuSign copy already has its page number printed on it. In that case the printed number must equal the PDF's final page number, and any edit that moves the last page means getting a newly signed copy.
- **Bold References**: If `III.A.7_BOLD_REFERENCES` fails, replace hand-typed `Figure 2.1` / `Table~\ref{...}` with `\FIG[A]{name}`, `\TABLE{name}` or `\cref{...}`.
- **Embedded Fonts**: If `IV.D_FONTS_EMBEDDED` fails, run `embed_fonts.sh` on the offending figures and rebuild.
- **Accessibility**: If `IV.PROQUEST_ACCESSIBILITY` fails, follow its details: `\DocumentMetadata` before `\documentclass`, `\usepackage{ucsf-accessibility}`, `pdftitle` in `\hypersetup`, `\FullPagePDF` instead of `\includepdf`, and a `\FigAlt` entry in `figure_alt_text.tex` for each listed graphic.
- **Table / Figure Captions**: Confirm table captions are positioned **above** the table and figure captions are positioned **below** the figure.

---

### Stage 6: ProQuest ETD Submission Checklist

Before final upload to ProQuest ETD:
1. Verify degree conferral date matches the last month of your graduation term and year.
2. Confirm both a UCSF email and a permanent personal email are entered in ProQuest.
3. Confirm committee members match your official Advance to Candidacy petition on file.
4. Verify all fonts are embedded and the PDF has no password protection or security restrictions (`IV.D_PDF_SPEC`).
5. Run the accessibility check ProQuest runs, and expect `0 failed`:
   ```bash
   python3 run_pipeline.py check-accessibility dissertation_master.pdf
   ```
   ProQuest's review report cites PDF/UA-1 clause and test numbers (e.g. "Test #3 | Clause 7.1"); the command prints the same numbers, so its output can be matched line by line against a report ProQuest sends back.

---

## 🧪 Continuous Integration & Testing

Run the test suite at any point to verify pipeline integrity:
```bash
python3 -m unittest discover tests -v
```
The full unit and integration suite must report `OK`.

---

## 📓 Lessons Learned (from a finished UCSF dissertation, Nov 2026)

These are the problems that came up while finishing a real dissertation with this pipeline; the template and validator now handle each one.

1. **Archive, never delete.** Before integrating a new manuscript version, copy the previous chapter sources and PDF into `archive/<date>_<what>/`. Treat the manuscript export (e.g. the Overleaf download) as read-only. Make dissertation-specific edits with a script that applies exact-match edits to it, and re-run that script when the manuscript changes, instead of hand-editing the generated chapter.
2. **Keep the extractor away from your real bibliography.** Run with its old defaults inside the dissertation folder, the extractor replaced the curated `.bib` with an empty one. Keep a dated backup of the bibliography, and only merge extracted entries after checking them (the extractor also matched some citations to the wrong papers).
3. **Page number distance:** `\footskip` is not the distance from the paper edge. 0.6in put the number 0.40in from the edge, which violates I.B.2.
4. **No full-page figures splitting text.** Text, then a figure page, then more text on the next page is not acceptable. The text should finish first, then the figure follows. The float policy plus a `\FloatBarrier` on every `\subsection` handles most cases; `layout_audit.py` finds the rest.
5. **Widows and orphans in the rubric's sense** include very short last lines of paragraphs, which TeX's widow penalty does not cover. `\parfillskip` discourages them but cannot forbid them, so check the audit.
6. **Bold every figure and table reference**, panel letter included, through macros, never by hand. Mixed bold and plain references are easy to miss when reading.
7. **The signed publishing agreement has its page number printed on it.** Include it unnumbered and keep the final page count fixed.
8. **Embed fonts in figures.** R figures and DocuSign PDFs fail IV.D until they go through `embed_fonts.sh`.
9. **Bibliography style:** one consistent format (initials, DOI rather than URL, no ISSN/notes), and optionally sentence-case titles (`sentence_case.py --dry-run` first: add any proper nouns it would lower-case with `--keep`).
10. **List of Abbreviations:** dataset or cohort names that are not abbreviations of anything (e.g. a cohort called by a code name) do not belong in it. Check expansions against the source rather than copying them from a draft, since drafts can carry wrong expansions.
11. **Keep tests hermetic.** A test that reads "the real file if present" will one day run inside the real dissertation folder.
12. **ProQuest rejects untagged PDFs.** Its accessibility review failed the finished dissertation on 10 PDF/UA-1 rules (52,218 instances), all from one cause: pdfLaTeX writes an untagged PDF. Lessons from fixing it:
    - Tag at compile time (`\DocumentMetadata`), do not repair the PDF afterwards. With TeX Live 2025 (LaTeX 2024-11) use LuaLaTeX: pdfLaTeX's tagging adds a page to every split `longtable`.
    - LuaLaTeX with `mathptmx` alone silently switches the body font to Latin Modern. Load `\usepackage[T1]{fontenc}` before `mathptmx` to keep Times and the original page breaks.
    - The 2024-11 tagging code overrides the caption package (labels lose bold, captions gain a line, floats move). `ucsf-accessibility.sty` restores it. After switching, compare the `.toc`/`.lof`/`.lot` page numbers with the previous build: identical lists mean figures and sections stayed on their pages.
    - veraPDF passes figures whose alt text is the file path (the tagging default). That is still inaccessible, so the template makes a missing `\FigAlt` a build error.
    - Signed DocuSign/Word pages carry fonts without Unicode maps and their own tags. Converting them to outlines (`embed_fonts.sh --forms`) and giving the page's full text as alt text fixes both, without touching the signatures.
    - Accented file names: macOS stores them decomposed, so alt-text keys are Unicode-normalized before matching.
