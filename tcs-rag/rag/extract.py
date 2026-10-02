"""Turn each raw PDF into per-page text.

Two reading strategies, chosen page by page:

* "rows"  - for table pages. Words carry x/y positions; words at (almost) the
            same height are one row, so we group by height and sort each row
            left to right. This keeps "Revenue ... 70,698 67,087 ..." together.
* "plain" - for everything else. PyMuPDF's default reading order follows the
            columns of the page, so paragraphs stay intact. (The row method
            would glue the columns of a multi-column page together line by line.)

How a page is classified (both numbers were tuned on real TCS pages):
1. numeric share: if few words are figures, it is prose  -> plain.
2. column score: many figures AND most long rows split into two chunks of ordinary
   words (two prose columns)  -> plain. Otherwise it is a table -> rows.
"""
import json
import re
from pathlib import Path

import pymupdf

from rag.config import RAW_DIR, ROOT

PROCESSED_DIR = ROOT / "data" / "processed" / "tcs"

ROW_TOLERANCE = 3         # PDF points; words closer than this vertically share a row
TABLE_THRESHOLD = 0.18    # numeric share at or above which a page *might* be a table
COLUMN_THRESHOLD = 0.25   # column score at or above which a page is prose in columns
MIN_GAP = 12              # PDF points; a gap this wide is a column gutter, not a space

# a figure: 1,234  2,55,324  (70)  12.5%  or a lone dash meaning "nil"
NUMBER = re.compile(r"^[\(\-]?\d[\d,\.]*\)?%?$|^[-–—]$")
# an ordinary word
ALPHA = re.compile(r"^[A-Za-z][A-Za-z'’\-]+[,.;:)]?$")


def numeric_ratio(text: str) -> float:
    words = text.split()
    if not words:
        return 0.0
    return sum(bool(NUMBER.match(w)) for w in words) / len(words)


def rows_of_words(page) -> list[list]:
    """Group the page's words into rows (same height), each sorted left to right."""
    words = sorted(page.get_text("words"), key=lambda w: (w[1] + w[3]) / 2)
    rows = []
    for w in words:
        y = (w[1] + w[3]) / 2
        if rows and abs(y - rows[-1][0]) < ROW_TOLERANCE:
            rows[-1][1].append(w)
        else:
            rows.append((y, [w]))
    return [sorted(ws, key=lambda w: w[0]) for _, ws in rows]


def rows_text(page) -> str:
    return "\n".join(" ".join(w[4] for w in row) for row in rows_of_words(page))


def column_score(page) -> float:
    """Share of long rows that split into two chunks of real words (prose columns)."""
    long_rows = two_prose = 0
    for row in rows_of_words(page):
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


def page_to_text(page) -> tuple[str, str]:
    """Return (text, method) for one page."""
    plain = page.get_text()
    if numeric_ratio(plain) >= TABLE_THRESHOLD and column_score(page) < COLUMN_THRESHOLD:
        return rows_text(page), "rows"
    return plain, "plain"


def extract_pdf(pdf_path: Path) -> dict:
    meta = json.loads(pdf_path.with_suffix(".meta.json").read_text(encoding="utf-8"))
    pages = []
    with pymupdf.open(pdf_path) as doc:
        for number, page in enumerate(doc, start=1):  # page numbers start at 1
            text, method = page_to_text(page)
            pages.append({"page": number, "method": method, "text": text})
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