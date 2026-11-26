# Tutorial: From Word Chapters to a UCSF-Ready Dissertation PDF

This guide is for you if you wrote your chapters in Microsoft Word and want a dissertation PDF that follows the UCSF formatting rules, **without needing to know how to program or use LaTeX**. You will type a handful of commands, and each one is explained.

Plan for about **1 hour** the first time (most of it is installing software), and a few minutes each time after that.

---

## What this tool does for you

You give it your Word chapters. It:

1. **Finds your citations.** It reads the links and DOIs in your chapters and looks up each paper's full details (authors, journal, year).
2. **Converts your chapters.** It turns each Word file into the format the dissertation template uses, with your headings, tables and citations in place.
3. **Builds the PDF.** It assembles the title page, copyright page, abstract, table of contents, your chapters, the reference list and the publishing agreement into one PDF.
4. **Checks the formatting.** It checks the result against 30 formatting checks based on the UCSF Dissertation Rubric (fonts, margins, page numbers, captions and so on) and tells you what, if anything, to fix.

You never have to write LaTeX yourself. You will make a few small text edits, such as typing your name and abstract.

---

## Part 1: One-time setup

You need three things on your computer.

### 1. Python (runs the tool)

- **Mac:** Open the **Terminal** app (press ⌘ + Space, type `Terminal`, press Enter). Type `python3 --version` and press Enter.
  - If you see something like `Python 3.11.4`, you're done.
  - If a window asks to install "command line developer tools", click **Install**, wait for it to finish, and try again.
- **Windows:** Download Python from [python.org/downloads](https://www.python.org/downloads/). During installation, **tick the box "Add Python to PATH"**. On Windows, type `python` wherever this guide says `python3`.

### 2. A LaTeX distribution (builds the PDF)

This is the software that typesets your dissertation. It is large (several GB), so start the download early.

- **Mac:** Install [MacTeX](https://www.tug.org/mactex/) (download `MacTeX.pkg` and double-click it).
- **Windows:** Install [TeX Live](https://www.tug.org/texlive/windows.html).

When it finishes, **close and reopen** Terminal (or Command Prompt) so it can find the new software.

### 2b. veraPDF (checks accessibility, recommended)

ProQuest checks that your PDF is accessible (usable with screen readers) and sends it back if it isn't. veraPDF runs the same check on your computer first.

- **Mac:** if you have [Homebrew](https://brew.sh), run `brew install verapdf`. Otherwise download the installer from [verapdf.org](https://verapdf.org/software/).
- **Windows:** download the installer from [verapdf.org](https://verapdf.org/software/).

### 3. This tool

1. Go to the project's GitHub page, click the green **Code** button, and choose **Download ZIP**.
2. Unzip it somewhere easy to find, such as your Desktop. You'll get a folder called `Dissertation_Template_and_Agentic_Pipeline` (or similar).

### Opening a terminal "inside" the tool's folder

Every command in this guide must be run from inside that folder.

- **Mac:** In Finder, right-click the folder → **New Terminal at Folder**. (If you don't see it: System Settings → Keyboard → Keyboard Shortcuts → Services → Files and Folders → enable "New Terminal at Folder".)
- **Windows:** Open the folder in File Explorer, click the address bar, type `cmd`, and press Enter.

### Check that everything works

Run this command. It checks the included example dissertation:

```
python3 run_pipeline.py validate-rubric -t synthetic_test_run/synthetic_master.tex
```

You should see a table of checks ending with:

```
Overall Status: COMPLIANT (ALL REQUIRED RULES PASSED)
```

If you see that, your setup works. 🎉

> **Tip:** you can open `synthetic_test_run/synthetic_master.pdf` to see what a finished result looks like.

---

## Part 2: Prepare your Word chapters

The tool can only use what it can recognize, so spend 10 minutes on each chapter:

| Do this in Word | Why |
|---|---|
| Put the **chapter title** in the **Heading 1** style (Home tab → Styles) | The first Heading 1 becomes the chapter title |
| Use **Heading 1** for main sections and **Heading 2** for subsections after that | These become the section levels in your dissertation |
| Make each in-text citation a **hyperlink** to the paper (e.g. `[1]` linked to `https://doi.org/10.1038/...`), **or** type the DOI in the text | This is how the tool finds your references |
| Use Word's **Insert → Table** for tables, with the caption ("Table 1. ...") in the paragraph just above | Tables and their captions are converted automatically |
| Save each chapter as its own `.docx` file | One file → one chapter |

Links the tool recognizes: `doi.org`, PubMed, PubMed Central, bioRxiv, medRxiv, and most journal article pages.

**Not converted automatically:**
- **Figures/images.** You'll add these in Part 5.
- **Citations inserted by a reference manager** (Zotero, EndNote, Mendeley) that are *not* links or DOIs may not be detected. Check your converted chapter in Part 3 and see the tips there.
- **Your Word reference list.** You don't need it; the dissertation builds its own REFERENCES section. You can delete it from the Word file before converting.

---

## Part 3: Convert your chapters

### Step 1: Make your working folder

Inside the tool's folder, create a new folder called `my_dissertation`. Then copy these three files **from `templates/latex/`** into it:

- `dissertation_master_template.tex` → rename the copy to **`dissertation.tex`**
- `Title_Page.pdf`
- `publishing_agreement.pdf`
- `ucsf-accessibility.sty` (makes the PDF accessible; don't edit it)
- `figure_alt_text.tex` (where you describe your figures; see Part 5)

Also copy your Word chapters into `my_dissertation`, named simply, for example `chapter1.docx`, `chapter2.docx`, `chapter3.docx`.

> Avoid spaces and special characters in file names. `chapter1.docx` is good; `Chapter 1 (FINAL v3).docx` causes trouble.

### Step 2: Find and look up your references

Run this command, listing all of your chapters (replace the email with your own; it lets the citation databases give your requests priority):

```
python3 run_pipeline.py extract-refs my_dissertation/chapter1.docx my_dissertation/chapter2.docx -o my_dissertation/references.bib -d my_dissertation/dois.txt -m my_dissertation/citation_map.json -e your.name@ucsf.edu
```

What this creates in `my_dissertation`:
- `references.bib`: your bibliography, with full details for every paper found
- `citation_map.json`: a lookup table the next step uses (you don't need to open it)
- `dois.txt`: a plain list of the DOIs found (handy for importing into Zotero)

It needs an internet connection and may take a minute. At the end it says how many references it found.

> **Running it again:** the tool won't replace a `references.bib` that already has entries, so your bibliography can't be wiped by accident. To redo this step, add `--overwrite` to the end of the command. The old file is kept as a backup named `references.bib.bak-` followed by the date and time. **Does that number look right?** If it's much lower than expected, your citations probably aren't links or DOIs (see Part 2).

### Step 3: Convert the chapters

```
python3 run_pipeline.py convert-docx my_dissertation/chapter1.docx my_dissertation/chapter2.docx -o my_dissertation/chapter1.tex my_dissertation/chapter2.tex -m my_dissertation/citation_map.json
```

List the Word files and the output names in the same order. This creates `chapter1.tex`, `chapter2.tex` and so on. As with references, an existing chapter file is never replaced unless you add `--overwrite` (the old one is backed up first). This protects any edits you made to the `.tex` files.

> **Quick check:** open `chapter1.tex` in any text editor (TextEdit on Mac, Notepad on Windows). It's plain text with some `\commands`. Your citations should look like `\cite{Horvath_2013}`. If you see raw web addresses or `[1]` instead, those citations weren't recognized.

---

## Part 4: Fill in your details

Open `my_dissertation/dissertation.tex` in a text editor. It looks technical, but you only change the plain-English text in a few places. Use **Find** (⌘F / Ctrl+F) to jump to each one:

| Search for | Replace with |
|---|---|
| `AUTHOR FULL NAME` (copyright page) | Your full name |
| `Copyright 2026` | The year you file |
| `TITLE OF THE DISSERTATION IN ALL CAPITAL LETTERS` (abstract) | Your title, in ALL CAPS |
| `AUTHOR FULL NAME IN ALL CAPITAL LETTERS` | Your name, in ALL CAPS |
| `A concise synthesis of the research problem` | Your abstract text |
| `Dedicated to my mentors` / `I express my deepest gratitude` / `Descriptions of student and co-author` | Your dedication, acknowledgements and contributions (or delete the section; they're optional) |
| `LIST OF ABBREVIATIONS` | Edit the example rows (`DNA`, `RNA`, `UCSF`) to your own abbreviations |

**Tell it which chapters to include.** Find this line:

```
\input{ch1_intro}
```

and replace it with one line per chapter, in order, with `\clearpage` between them:

```
\input{chapter1}
\clearpage
\input{chapter2}
```

**Replace the two PDFs:**
- `Title_Page.pdf` → your official UCSF title page (the DocuSign-signed PDF), saved with the same name.
- `publishing_agreement.pdf` → your signed publishing agreement, saved with the same name.

**Then prepare them for the PDF** (run this again whenever you replace either file):

```
bash agentic_scripts/embed_fonts.sh -o my_dissertation/build_embedded --forms my_dissertation/Title_Page.pdf my_dissertation/publishing_agreement.pdf
```

This turns their text into outlines, which makes them pass ProQuest's accessibility check without changing how they look. Because the text is no longer readable by software, open `figure_alt_text.tex` and replace the two example descriptions at the top with **the full text of your title page and of your signed agreement** (who signed and the date included). Screen readers read that text instead.

**Title and name in the PDF's properties:** in `dissertation.tex`, find `pdftitle={DISSERTATION TITLE}` and `pdfauthor={AUTHOR FULL NAME}` and fill in your title and name exactly as on the title page.

**Publishing agreement page number:** the agreement must be the last page and must be numbered. The signed copy UCSF sends back usually has its page number already printed on it. If yours does, open `dissertation.tex`, find the line `\newcommand{\AgreementPageStyle}{fancy}` and change `fancy` to `empty`, otherwise the page will show two numbers. Then check that the printed number matches the actual last page of your PDF. If later edits change the page count, you will need a newly signed copy.

### Special characters in your text

Inside the `.tex` files, a few characters have special meanings. If you type them yourself, put a backslash before them: `%` → `\%`, `&` → `\&`, `#` → `\#`, `_` → `\_`. (The converter already does this for text that came from Word.)

---

## Part 5: Build the PDF and check it

### Build

```
python3 run_pipeline.py build -t my_dissertation/dissertation.tex
```

If it works, you'll see `Build SUCCESS!` and the page count. Your PDF is `my_dissertation/dissertation.pdf`. Open it and look through it.

### Check against the UCSF rubric

```
python3 run_pipeline.py validate-rubric -t my_dissertation/dissertation.tex
```

Each rule shows `[PASS]` or `[FAIL]`. For every failure, the report explains what's wrong and how to fix it. **Always build before checking**: the check reads the files the build produces.

### Check accessibility (what ProQuest checks)

```
python3 run_pipeline.py check-accessibility my_dissertation/dissertation.pdf
```

You want `PDF/UA-1 compliant ... 0 failed`. Otherwise each problem is listed with the name ProQuest uses for it and what to do. This needs veraPDF (Part 1, step 2b).

### Adding figures

Put your image files (`.pdf`, `.png` or `.jpg`) in `my_dissertation`. Then, in the chapter's `.tex` file, paste this where the figure should go and edit the file name and caption:

```
\begin{figure}[htbp]
    \centering
    \includegraphics[width=0.9\textwidth]{figure1.png}
    \caption[Short title for the List of Figures]{{\bfseries Short title.} Longer description of the figure.}
    \label{fig:my_figure}
\end{figure}
```

Captions go *below* figures, as UCSF requires. To refer to it in your text, write `Figure~\ref{fig:my_figure}`.

**Every figure needs a description for screen readers** ("alt text"). Open `figure_alt_text.tex` and add a line with the image's file name (without `.png`/`.pdf`):

```
\FigAlt{figure1}{Bar chart of clock accuracy in five groups; accuracy is lowest in the two groups with the most African ancestry.}
```

Say what kind of graphic it is, what it shows, and the main finding, in one to three sentences. Don't repeat the caption: it is read right after. If you forget, the build stops with `No alt text for graphic` and names the file.

**Text in another language** (for example a dedication in Spanish): put the paragraphs between `\begin{langtext}{es}` and `\end{langtext}` so screen readers pronounce them correctly (`es` Spanish, `fr` French, `pt` Portuguese, ...).

---

## Common problems

| You see | What to do |
|---|---|
| `python3: command not found` (Mac) / `'python3' is not recognized` (Windows) | Mac: redo Part 1, step 1. Windows: use `python` instead of `python3`, or reinstall Python with "Add Python to PATH" ticked. |
| `latexmk: command not found` or the build can't start | The LaTeX install (Part 1, step 2) isn't finished, or you didn't reopen Terminal afterwards. |
| `File not found` | You're not in the tool's folder (see "Opening a terminal inside the tool's folder"), or a file name is misspelled. |
| `Build FAILED` with an error message | Read the message: it usually names the problem and line. Most often it's an unescaped `%`, `&`, `#` or `_` you typed (see Part 4). |
| `[?]` or **"citation undefined"** in the PDF | A `\cite{...}` key in a chapter isn't in `references.bib`. Rerun Part 3, Step 2 with **all** chapters listed, adding `--overwrite`. |
| Fewer references found than expected | Your citations aren't hyperlinks or DOIs. Add links in Word (Part 2) and rerun Part 3. |
| `Compilation Log Quality` fails | The build had errors. Fix those first, rebuild, then re-check. |
| `No alt text for graphic` | Add a `\FigAlt{...}{...}` line for that file to `figure_alt_text.tex` (Part 5, "Adding figures"). |
| `LuaTeX is required` | Something built the PDF with pdfLaTeX. Use `python3 run_pipeline.py build`; on Overleaf, set Menu → Compiler → **LuaLaTeX**. |
| `veraPDF not found` | Install it (Part 1, step 2b), close and reopen Terminal, and rerun. |

---

## Updating after you edit a chapter

If you change a Word chapter, rerun **Part 3, Steps 2 and 3** for all chapters, then **Part 5**. This **replaces** `chapter1.tex`, `chapter2.tex` and so on, so any edits you made directly in those files (like added figures) will be lost.

**Recommended:** make text edits in Word until your chapters are final, then add figures and do final tweaks in the `.tex` files.

> **Prefer an online editor?** Once your `my_dissertation` folder builds successfully, you can upload the whole folder to [Overleaf](https://www.overleaf.com) (New Project → Upload Project, as a ZIP) and make final edits there with a live preview. In Overleaf, open **Menu → Compiler** and choose **LuaLaTeX**, or the build stops with "LuaTeX is required".

---

## Getting more help

- **`README.md`** lists every command and option.
- **`dissertation_agentic_workflow_guide.md`** explains how to use an AI assistant (such as Claude) to run these steps and fix formatting problems for you.
- The full UCSF rubric is in the `rubric/` folder.
