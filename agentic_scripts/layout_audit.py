#!/usr/bin/env python3
"""Page-layout audit of a compiled dissertation PDF against the UCSF rubric layout rules.

The rubric validator reads the .tex source; this reads the finished PDF, which is the only way to see
where floats and paragraph ends actually landed. Run it after every rebuild and expect "0 issue(s)",
then look at the pages it names (it works from extracted text, so confirm by eye).
Requires Ghostscript (gs). Assumes US Letter with 1in margins and Arabic-numbered body pages.

Uses Ghostscript's txtwrite device (with coordinates) to read every line on every page.
Reports, for body pages (arabic numbered, chapters 1-4):
  - FLOAT PAGE MID-TEXT : a page with no running text whose previous text page ends mid-paragraph,
                          or whose next text page continues the same subsection (no new heading)
  - STRANDED HEADING    : a section/subsection heading that is the last text line on a page
  - SHORT LAST LINE     : a paragraph whose last line is < 20% of the text width (rubric "widow")
  - ORPHAN LINE         : a page whose first text line is the last line of a paragraph started on
                          the previous page (rubric "orphan"; TeX widow)
  - GAP                 : a text page that is less than half full before a float page
Usage: python3 layout_audit.py dissertation_master.pdf [--verbose]
Exit status: 0 when no issues are found, 1 otherwise.
"""
import re, subprocess, sys, html

pdf = sys.argv[1] if len(sys.argv) > 1 else "dissertation_master.pdf"
xml = subprocess.run(["gs", "-q", "-dNOPAUSE", "-dBATCH", "-sDEVICE=txtwrite", "-dTextFormat=0",
                      "-sOutputFile=-", pdf], capture_output=True, text=True, errors="replace").stdout
pages = re.split(r"<page\b", xml)[1:]

LEFT, RIGHT = 72, 540          # 1in margins on 8.5in paper (pt)
WIDTH = RIGHT - LEFT
TOP, BOTTOM = 72, 720          # text block (pt from top)


def lines_of(page):
    """Return list of (y, x0, x1, text, size) per visual line (merging spans with same baseline)."""
    spans = []
    for m in re.finditer(r'<span bbox="(\d+) (\d+) (\d+) (\d+)" font="([^"]*)" size="([\d.]+)">(.*?)</span>', page, flags=re.S):
        x0, y0, x1, y1 = map(int, m.group(1, 2, 3, 4))
        chars = "".join(html.unescape(c) for c in re.findall(r'c="([^"]*)"', m.group(7)))
        spans.append((y1, x0, x1, chars, float(m.group(6)), m.group(5)))
    rows = {}
    for y, x0, x1, ch, sz, font in spans:
        key = next((k for k in rows if abs(k - y) <= 2), y)
        r = rows.setdefault(key, [10 ** 6, 0, "", 0, ""])
        r[0] = min(r[0], x0); r[1] = max(r[1], x1); r[2] += ch; r[3] = max(r[3], sz); r[4] = r[4] or font
    return [(y, *rows[y]) for y in sorted(rows)]


info = []
for i, pg in enumerate(pages, 1):
    ls = lines_of(pg)
    if not ls:
        info.append(None); continue
    num_line = ls[-1] if re.fullmatch(r"\s*[0-9ivxl]+\s*", ls[-1][3]) and ls[-1][0] > BOTTOM else None
    body = [l for l in ls if l is not num_line]
    # running text = 12pt-ish lines (size >= 11.5) inside the text block; captions/legends are smaller
    text = [l for l in body if l[4] >= 11.5 and TOP - 5 <= l[0] <= BOTTOM + 5 and LEFT - 5 <= l[1]]
    cap = [l for l in body if re.match(r"\s*(Figure|Table)\s*\d+\.\d+:", l[3])]
    info.append(dict(n=i, num=num_line[3].strip() if num_line else "?", text=text, cap=cap, body=body))

issues = []
heading_re = re.compile(r"^\s*\d+\.\d+(\.\d+)?\s*[A-Z]")
arabic = [p for p in info if p and p["num"].isdigit()]
for k, p in enumerate(arabic):
    pnum = int(p["num"])
    if pnum > 200:
        continue
    joined = " ".join(l[3] for l in p["body"])
    if re.search(r"^\s*REFERENCES\s*$", joined) or "REFERENCES" in [l[3].strip() for l in p["body"][:2]]:
        break
    text = p["text"]
    # pages that are only float(s): few 12pt lines and at least one caption
    float_only = p["cap"] and len(text) <= 2
    if float_only and 0 < k < len(arabic) - 1:
        # previous page that carries any running text (a closing line on a float page counts);
        # next page of running text that is not itself a float/table page
        prev = next((q for q in reversed(arabic[:k]) if q["text"]), None)
        nxt = next((q for q in arabic[k + 1:] if q["text"] and not q["cap"]), None)
        if prev and nxt:
            # if the float page itself carries the paragraph's closing line(s), the text finished before the float
            last = (text[-1][3].strip() if text else prev["text"][-1][3].strip())
            first = nxt["text"][0][3].strip()
            mid_par = not re.search(r"[.:)?]$", last)
            same_sub = not heading_re.match(first) and not first.startswith("CHAPTER")
            if mid_par or same_sub:
                issues.append((pnum, "FLOAT PAGE MID-TEXT", f"prev p.{prev['num']} ends '{last[-40:]}' | next p.{nxt['num']} starts '{first[:40]}'"))
        if prev and len(prev["text"]) < 12 and not prev["cap"]:
            issues.append((int(prev["num"]), "GAP", f"only {len(prev['text'])} text lines before float page p.{pnum}"))
    if text and not float_only:
        last = text[-1][3].strip()
        if heading_re.match(last) and len(last) < 130:
            issues.append((pnum, "STRANDED HEADING", last[:70]))
    # short last lines: a text line that ends a paragraph (next line indented or blank-gap) and is short
    for a, b in zip(text, text[1:] + [None]):
        y, x0, x1, s, sz, font = a
        w = x1 - x0
        ends_par = b is None or (b[1] - LEFT > 15) or (b[0] - y > 40)
        if ends_par and w < 0.2 * WIDTH and x0 < LEFT + 5 and not heading_re.match(s) and len(s.strip()) > 0 \
                and not re.fullmatch(r"\s*[0-9ivxl]+\s*", s) and b is not None:
            issues.append((pnum, "SHORT LAST LINE", repr(s.strip()[:40])))
    # orphan: first text line of page is short and ends a paragraph
    if text and len(text) > 1 and not float_only:
        y, x0, x1, s, sz, font = text[0]
        nx = text[1]
        if (x1 - x0) < 0.6 * WIDTH and x0 < LEFT + 5 and (nx[1] - LEFT > 15 or nx[0] - y > 40) and not heading_re.match(s):
            issues.append((pnum, "ORPHAN LINE", repr(s.strip()[:40])))

if "--verbose" in sys.argv:
    for k, p in enumerate(arabic):
        if p["cap"] and len(p["text"]) <= 2 and 0 < k < len(arabic) - 1:
            prev = next((q for q in reversed(arabic[:k]) if q["text"] and not (q["cap"] and len(q["text"]) <= 2)), None)
            nxt = next((q for q in arabic[k + 1:] if q["text"] and not (q["cap"] and len(q["text"]) <= 2)), None)
            print(f"float page p.{p['num']}: prev p.{prev['num']} ({len(prev['text'])} lines) ends '{prev['text'][-1][3].strip()[-30:]}' | next p.{nxt['num']} starts '{nxt['text'][0][3].strip()[:30]}'")
for pnum, kind, msg in sorted(issues):
    print(f"p.{pnum:<4} {kind:20s} {msg}")
print(f"{len(issues)} issue(s)")
sys.exit(1 if issues else 0)
