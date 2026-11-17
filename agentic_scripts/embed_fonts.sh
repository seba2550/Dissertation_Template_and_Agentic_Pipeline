#!/usr/bin/env bash
# UCSF Rubric IV.D: every font in the submitted PDF must be embedded.
# R's pdf() device leaves Helvetica unembedded, and the DocuSign title page / publishing agreement
# leave Arial unembedded. This writes font-embedded copies into build_embedded/ (flat, same file
# names). Originals are never modified. The master template's \graphicspath searches build_embedded/
# first, so nothing in the .tex needs to change.
# Images are passed through without downsampling or recompression.
#
# Usage: agentic_scripts/embed_fonts.sh [-o OUTDIR] <file.pdf | directory>...
#   e.g. agentic_scripts/embed_fonts.sh figures/ Title_Page.pdf publishing_agreement.pdf
# Run it from the folder that holds the master .tex, whenever a figure, the title page or the
# publishing agreement changes. Up-to-date copies are skipped.
set -euo pipefail
OUT=build_embedded
if [[ "${1:-}" == "-o" ]]; then OUT="$2"; shift 2; fi
if [[ $# -eq 0 ]]; then sed -n '2,13p' "$0"; exit 1; fi
command -v gs >/dev/null || { echo "Ghostscript (gs) is required" >&2; exit 1; }
mkdir -p "$OUT"

files=()
for arg in "$@"; do
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
  gs -q -dNOPAUSE -dBATCH -dSAFER -sDEVICE=pdfwrite -dCompatibilityLevel=1.5 \
     -dEmbedAllFonts=true -dSubsetFonts=true -dAutoRotatePages=/None \
     -dDownsampleColorImages=false -dDownsampleGrayImages=false -dDownsampleMonoImages=false \
     -dAutoFilterColorImages=false -dAutoFilterGrayImages=false \
     -dColorImageFilter=/FlateEncode -dGrayImageFilter=/FlateEncode \
     -sOutputFile="$OUT/$b" -c "<</NeverEmbed [ ] /AlwaysEmbed [/Helvetica /Helvetica-Bold /Helvetica-Oblique /Helvetica-BoldOblique /Symbol /ZapfDingbats /Times-Roman /Courier /Courier-Bold /ArialMT /Arial-BoldMT /ArialUnicodeMS /TimesNewRomanPSMT /TimesNewRomanPS-BoldMT /TimesNewRomanPS-ItalicMT]>> setdistillerparams" -f "$f"
  echo "embedded: $b"
done
