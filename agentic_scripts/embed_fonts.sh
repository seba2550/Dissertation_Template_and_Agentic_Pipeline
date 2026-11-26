#!/usr/bin/env bash
# UCSF Rubric IV.D: every font in the submitted PDF must be embedded.
# R's pdf() device leaves Helvetica unembedded, and the DocuSign title page / publishing agreement
# leave Arial unembedded. This writes font-embedded copies into build_embedded/ (flat, same file
# names). Originals are never modified. The master template's \graphicspath searches build_embedded/
# first, so nothing in the .tex needs to change.
# Images are passed through without downsampling or recompression.
#
# Usage: agentic_scripts/embed_fonts.sh [-o OUTDIR] <file.pdf | directory>... [--forms <form.pdf>...]
#   e.g. agentic_scripts/embed_fonts.sh figures/ --forms Title_Page.pdf publishing_agreement.pdf
# Run it from the folder that holds the master .tex, whenever a figure, the title page or the
# publishing agreement changes. Up-to-date copies are skipped.
# --forms: files after it are signed forms (DocuSign title page, publishing agreement). Their text is
# turned into vector outlines and their own tags are dropped: DocuSign/Word fonts lack Unicode maps and
# their tags clash with the dissertation's, both failing ProQuest's accessibility (PDF/UA-1) check.
# The page looks identical; its text goes in figure_alt_text.tex as the page's alt text.
set -euo pipefail
OUT=build_embedded
if [[ "${1:-}" == "-o" ]]; then OUT="$2"; shift 2; fi
if [[ $# -eq 0 ]]; then sed -n '2,17p' "$0"; exit 1; fi
command -v gs >/dev/null || { echo "Ghostscript (gs) is required" >&2; exit 1; }
mkdir -p "$OUT"

files=()
forms=()
in_forms=0
for arg in "$@"; do
  if [[ "$arg" == "--forms" ]]; then in_forms=1; continue; fi
  if (( in_forms )); then
    if [[ -f "$arg" ]]; then forms+=("$arg"); files+=("$arg"); else echo "skipping (not found): $arg" >&2; fi
    continue
  fi
  if [[ -d "$arg" ]]; then
    while IFS= read -r -d '' f; do files+=("$f"); done < <(find "$arg" -maxdepth 1 -iname '*.pdf' -print0)
  elif [[ -f "$arg" ]]; then
    files+=("$arg")
  else
    echo "skipping (not found): $arg" >&2
  fi
done

if [[ ${#files[@]} -eq 0 ]]; then echo "no PDFs found" >&2; exit 1; fi
# build_embedded/ is flat: warn when two inputs share a file name (the later one would win)
dups=$(for f in "${files[@]}"; do basename "$f"; done | sort | uniq -d)
[[ -n "$dups" ]] && echo "WARNING: inputs share these file names; only the last copy is kept: $dups" >&2

for f in "${files[@]}"; do
  b=$(basename "$f")
  if [[ -e "$OUT/$b" && "$OUT/$b" -nt "$f" && "$OUT/$b" -nt "$0" ]]; then continue; fi
  is_form=0
  for g in "${forms[@]+"${forms[@]}"}"; do [[ "$g" == "$f" ]] && is_form=1; done
  if (( is_form )); then
    gs -q -dNOPAUSE -dBATCH -dSAFER -sDEVICE=pdfwrite -dCompatibilityLevel=1.7 \
       -dNoOutputFonts -dPreserveMarkedContent=false -dPreserveAnnots=false -dAutoRotatePages=/None \
       -dDownsampleColorImages=false -dDownsampleGrayImages=false -dDownsampleMonoImages=false \
       -dAutoFilterColorImages=false -dAutoFilterGrayImages=false \
       -dColorImageFilter=/FlateEncode -dGrayImageFilter=/FlateEncode \
       -sOutputFile="$OUT/$b" -f "$f"
    echo "outlined form: $b"
    continue
  fi
  gs -q -dNOPAUSE -dBATCH -dSAFER -sDEVICE=pdfwrite -dCompatibilityLevel=1.5 \
     -dEmbedAllFonts=true -dSubsetFonts=true -dAutoRotatePages=/None \
     -dDownsampleColorImages=false -dDownsampleGrayImages=false -dDownsampleMonoImages=false \
     -dAutoFilterColorImages=false -dAutoFilterGrayImages=false \
     -dColorImageFilter=/FlateEncode -dGrayImageFilter=/FlateEncode \
     -sOutputFile="$OUT/$b" -c "<</NeverEmbed [ ] /AlwaysEmbed [/Helvetica /Helvetica-Bold /Helvetica-Oblique /Helvetica-BoldOblique /Symbol /ZapfDingbats /Times-Roman /Courier /Courier-Bold /ArialMT /Arial-BoldMT /ArialUnicodeMS /TimesNewRomanPSMT /TimesNewRomanPS-BoldMT /TimesNewRomanPS-ItalicMT]>> setdistillerparams" -f "$f"
  echo "embedded: $b"
done
