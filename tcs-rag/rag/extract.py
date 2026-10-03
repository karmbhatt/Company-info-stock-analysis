"""Turn each raw PDF into per-page text.

Two reading strategies, chosen page by page:

* "rows"  - for table pages. Words carry x/y positions; words at (almost) the
            same height are one row, so we group by height and sort each row
            left to right. This keeps "Revenue ... 70,698 67,087 ..." together.
* "plain" - for everything else. PyMuPDF's default reading order follows the
            columns of the page, so paragraphs stay intact. (The row method
            would glue the columns of a multi-column page together line by line.)

Two-page spreads: some PDFs (e.g. the FY2025 report) put two printed pages side by
side on one very wide PDF page. We cut such a page down the middle and treat the left
and right halves as separate pages, otherwise the row method would glue the left
page's lines to the right page's lines.

How a page is classified (both numbers were tuned on real TCS pages):
1. numeric share: if few words are figures, it is prose  -> plain.
2. numeric share of 30% or more: it is a table  -> rows.
3. in between: if most long rows split into two chunks of ordinary words (two prose
   columns) -> plain. Otherwise it is a table -> rows.
"""
import json
import re
from pathlib import Path

import pymupdf

from rag.config import RAW_DIR, ROOT

PROCESSED_DIR = ROOT / "data" / "processed" / "tcs"

ROW_TOLERANCE = 3         # PDF points; words closer than this vertically share a row
TABLE_THRESHOLD = 0.18    # numeric share at or above which a page *might* be a table
STRONG_TABLE = 0.30       # numeric share at or above which a page is a table, no matter what
COLUMN_THRESHOLD = 0.25   # column score at or above which a page is prose in columns
MIN_GAP = 12              # PDF points; a gap this wide is a column gutter, not a space
SPREAD_RATIO = 1.4        # a PDF page wider than 1.4 x its height is a two-page spread

# a figure: 1,234  2,55,324  (70)  12.5%  or a lone dash meaning "nil"
NUMBER = re.compile(r"^[\(\-]?\d[\d,\.]*\)?%?$|^[-–—]$")
# an ordinary word
ALPHA = re.compile(r"^[A-Za-z][A-Za-z'’\-]+[,.;:)]?$")


def numeric_ratio(text: str) -> float:
    words = text.split()
    if not words:
        return 0.0
    return sum(bool(NUMBER.match(w)) for w in words) / len(words)


def page_units(page):
    """Yield (clip, side) for each printed page found on this PDF page."""
    r = page.rect
    if r.width > SPREAD_RATIO * r.height:               # a two-page spread
        mid = r.x0 + r.width / 2
        yield pymupdf.Rect(r.x0, r.y0, mid, r.y1), "left"
        yield pymupdf.Rect(mid, r.y0, r.x1, r.y1), "right"
    else:
        yield r, None


def rows_of_words(page, clip) -> list[list]:
    """Group the words inside `clip` into rows (same height), each sorted left to right."""
    words = sorted(page.get_text("words", clip=clip), key=lambda w: (w[1] + w[3]) / 2)
    rows = []
    for w in words:
        y = (w[1] + w[3]) / 2
        if rows and abs(y - rows[-1][0]) < ROW_TOLERANCE:
            rows[-1][1].append(w)
        else:
            rows.append((y, [w]))
    return [sorted(ws, key=lambda w: w[0]) for _, ws in rows]


def rows_text(page, clip) -> str:
    return "\n".join(" ".join(w[4] for w in row) for row in rows_of_words(page, clip))


def column_score(page, clip) -> float:
    """Share of long rows that split into two chunks of real words (prose columns)."""
    long_rows = two_prose = 0
    for row in rows_of_words(page, clip):
        if len(row) < 8:
            continue
        long_rows += 1
        gap, i = max((row[k + 1][0] - row[k][2], k) for k in range(len(row) - 1))
        if gap < MIN_GAP:
            continue
        left = sum(bool(ALPHA.match(w[4])) for w in row[: i + 1])
        right = sum(bool(ALPHA.match(w[4])) for w in row[i + 1 :])
        if left >= 4 and right >= 4:
            two_prose += 1
    return two_prose / long_rows if long_rows else 0.0


def page_to_text(page, clip) -> tuple[str, str]:
    """Return (text, method) for one printed page (the part of `page` inside `clip`)."""
    plain = page.get_text(clip=clip)
    share = numeric_ratio(plain)
    if share >= STRONG_TABLE or (share >= TABLE_THRESHOLD and column_score(page, clip) < COLUMN_THRESHOLD):
        return rows_text(page, clip), "rows"
    return plain, "plain"


def extract_pdf(pdf_path: Path) -> dict:
    meta = json.loads(pdf_path.with_suffix(".meta.json").read_text(encoding="utf-8"))
    pages, page_no = [], 0
    with pymupdf.open(pdf_path) as doc:
        for pdf_page_no, page in enumerate(doc, start=1):
            for clip, side in page_units(page):
                page_no += 1   # a spread counts as two pages (printed page numbers can still differ)
                text, method = page_to_text(page, clip)
                pages.append({"page": page_no, "pdf_page": pdf_page_no, "side": side,
                              "method": method, "text": text})
    return {**meta, "pages": pages}


def main():
    for pdf_path in sorted(RAW_DIR.rglob("*.pdf")):
        result = extract_pdf(pdf_path)
        out_dir = PROCESSED_DIR / result["document_type"]
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{result['id']}.json"
        out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        n_rows = sum(p["method"] == "rows" for p in result["pages"])
        print(f"{result['id']:<30} {len(result['pages'])} pages "
              f"({n_rows} read as tables) -> {out_path.name}")


if __name__ == "__main__":
    main()