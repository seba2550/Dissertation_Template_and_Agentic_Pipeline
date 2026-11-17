"""Convert BibTeX title fields to sentence case, keeping acronyms, mixed-case names and proper nouns.

Usage:
  python3 sentence_case.py references.bib --dry-run        # list the titles that would change
  python3 sentence_case.py references.bib                  # rewrite in place (backup: <file>.bak-<timestamp>)
  python3 sentence_case.py references.bib -o out.bib       # write elsewhere
  python3 sentence_case.py references.bib --keep Zika --keep "Hutterite"   # extra proper nouns

Review the --dry-run output first: proper nouns missing from the lists below get lower-cased.

Rules
- First word of the title, and the first word after ':', '?' or '.', are left as they are.
- Words with internal capitals or digits (DNA, GrimAge, KLF14, meQTL) are kept and brace-protected.
- Proper nouns (single words and multi-word names below) are kept and brace-protected.
- Every other word that starts with a capital is lower-cased.
"""
import re

PROPER_WORDS = {
    "African", "Africans", "American", "Americans", "Alzheimer's", "Alzheimer", "Parkinson's", "Parkinson",
    "Bioconductor", "BeadChip", "Black", "Hispanic", "Hispanics", "Latino", "Latinos", "Illumina", "Infinium",
    "Krüppel", "Kruppel", "European", "Europeans", "Asian", "Asians", "Gompertz", "Mendelian", "Bayesian",
    "Mexican", "Puerto", "Rican", "Ricans", "Cuban", "Cubans", "Peruvian", "Peruvians", "English", "Chinese",
    "Finnish", "Swedish", "Japanese", "Native", "Hawaiian", "Caribbean", "Ashkenazi", "Yoruba",
}
PROPER_PHRASES = [
    "UK Biobank", "Voting Rights Act", "Jim Crow", "United States", "Social Epigenomics Program",
    "All of Us Research Program", "All of Us' Research Program", "All of Us", "Young Finns", "Genome Browser Database",
    "Women's Health Initiative", "Disease Neuroimaging Initiative", "Framingham Heart Study",
    "Health and Retirement Study", "Atherosclerosis Risk in Communities", "Grady Trauma Project", "Human Genome Project",
]


def _protected_spans(plain):
    spans = []
    for ph in PROPER_PHRASES:
        for m in re.finditer(r"(?<![A-Za-z])" + re.escape(ph) + r"(?![A-Za-z])", plain, flags=re.I):
            spans.append((m.start(), m.end()))
    return spans


def sentence_case(title):
    if "\\" in title and re.search(r"\\(?!&|%|textless|textgreater)[a-zA-Z]", title.replace("``", "").replace("''", "")):
        pass  # titles with TeX commands are still processed word by word; commands are left untouched
    # plain text with braces removed, to locate phrases
    plain = title.replace("{", "").replace("}", "")
    spans = _protected_spans(plain)
    out = []
    pos_plain = 0
    start_of_sentence = True
    after_colon = False
    # tokens: words (with braces and inner hyphen/slash pieces) and separators
    for tok in re.split(r"(\s+)", title):
        if tok == "" or tok.isspace():
            out.append(tok)
            pos_plain += len(tok)
            continue
        tok_plain = tok.replace("{", "").replace("}", "")
        tok_start = pos_plain
        pos_plain += len(tok_plain)
        in_phrase = any(a <= tok_start < b for a, b in spans)
        pieces = re.split(r"([\-/–])", tok)
        new_pieces = []
        piece_pos = tok_start
        for i, pc in enumerate(pieces):
            if pc in ("-", "/", "–"):
                new_pieces.append(pc); piece_pos += 1; continue
            core_plain = pc.replace("{", "").replace("}", "")
            p_start = piece_pos
            piece_pos += len(core_plain)
            word = re.sub(r"^[^\w$\\]+|[^\w']+$", "", core_plain)
            first = start_of_sentence and i == 0 and not after_colon
            if not word or "\\" in pc or "$" in pc:
                new_pieces.append(pc); continue
            w0 = p_start + (len(core_plain) - len(core_plain.lstrip("`'\"([")))
            in_ph = any(a <= w0 < b for a, b in spans)
            mixed = bool(re.search(r"[A-Z]", word[1:]) or (re.search(r"\d", word) and re.search(r"[A-Za-z]", word)))
            keep = first or mixed or in_ph or word in PROPER_WORDS or word.rstrip("'s") in PROPER_WORDS \
                or (word == "White" and not re.match(r"^-?\{?[Mm]atter", "".join(pieces[i + 1:]).lstrip("-")))
            if keep:
                if (mixed or in_ph or word in PROPER_WORDS or word == "White") and not first and "{" not in pc:
                    pc = pc.replace(word, "{" + word + "}", 1)
                new_pieces.append(pc)
            else:
                unbr = pc
                # drop Zotero-style protection around ordinary capitalised words, then lower-case
                unbr = re.sub(r"\{([A-Z][a-zà-ÿ']*)\}", r"\1", unbr)
                if re.match(r"^[^\w]*[A-Z][a-zà-ÿ']*", unbr.replace("{", "").replace("}", "")) and "{" not in unbr:
                    unbr = re.sub(r"[A-Z]", lambda m: m.group(0).lower(), unbr, count=1)
                new_pieces.append(unbr)
        out.append("".join(new_pieces))
        start_of_sentence = bool(re.search(r"[:?.!]\}?$", tok_plain))
        after_colon = bool(re.search(r":\}?$", tok_plain))  # house style: lower-case after a colon
    return "".join(out)


def _find_field(entry, name):
    m = re.search(r"(?im)^\s*" + name + r"\s*=\s*\{|(?<=[,\s])" + name + r"\s*=\s*\{", entry)
    if not m:
        return None
    i = m.end(); depth = 1
    while depth and i < len(entry):
        if entry[i] == "{": depth += 1
        elif entry[i] == "}": depth -= 1
        i += 1
    return m.end(), i - 1


def apply(bibtext, keys=None):
    """Sentence-case the title field of every @article/@inproceedings/@book entry (or only `keys`)."""
    out = []; changed = []
    parts = re.split(r"(?m)(?=^@\w+\{)", bibtext)
    for part in parts:
        m = re.match(r"@(\w+)\{([^,\s]+),", part)
        if not m or m.group(1).lower() in ("misc", "online", "software", "string", "comment", "preamble") or (keys and m.group(2) not in keys):
            out.append(part); continue
        span = _find_field(part, "title")
        if not span:
            out.append(part); continue
        a, b = span
        old = part[a:b]; new = sentence_case(old)
        if new != old:
            changed.append((m.group(2), old, new))
        out.append(part[:a] + new + part[b:])
    return "".join(out), changed


def main(argv=None):
    import argparse, shutil, sys, time
    ap = argparse.ArgumentParser(description="Sentence-case the title field of every entry in a .bib file.")
    ap.add_argument("bib")
    ap.add_argument("-o", "--output", help="Output .bib (default: rewrite the input, after backing it up)")
    ap.add_argument("--dry-run", action="store_true", help="Only print old -> new titles")
    ap.add_argument("--keep", action="append", default=[],
                    help="Extra proper noun (word or phrase) to keep capitalised; repeatable")
    args = ap.parse_args(argv)
    for k in args.keep:
        (PROPER_PHRASES.append(k) if " " in k else PROPER_WORDS.add(k))
    text = open(args.bib, encoding="utf-8").read()
    new, changed = apply(text)
    for key, old, nw in changed:
        print(f"{key}\n  - {old}\n  + {nw}")
    print(f"{len(changed)} title(s) {'would change' if args.dry_run else 'changed'}")
    if args.dry_run or not changed:
        return 0
    out = args.output or args.bib
    if out == args.bib:
        backup = f"{args.bib}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
        shutil.copy2(args.bib, backup)
        print(f"backup: {backup}", file=sys.stderr)
    open(out, "w", encoding="utf-8").write(new)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
