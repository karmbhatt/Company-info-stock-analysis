"""Turn each raw PDF into per-page text, keeping table rows together.

Words in a PDF carry x/y positions. Words at (almost) the same height are one
row, so we group by height and sort each row left to right.
"""
import json
from pathlib import Path

import pymupdf

from rag.config import RAW_DIR, ROOT

PROCESSED_DIR = ROOT / "data" / "processed" / "tcs"
ROW_TOLERANCE = 3  # PDF points; words closer than this vertically share a row


def page_to_text(page) -> str:
    words = sorted(page.get_text("words"), key=lambda w: (w[1] + w[3]) / 2)

    rows = []
    for w in words:
        y = (w[1] + w[3]) / 2
        if rows and abs(y - rows[-1]["y"]) < ROW_TOLERANCE:
            rows[-1]["words"].append(w)
        else:
            rows.append({"y": y, "words": [w]})

    lines = []
    for row in rows:
        ordered = sorted(row["words"], key=lambda w: w[0])
        lines.append(" ".join(w[4] for w in ordered))
    return "\n".join(lines)


def extract_pdf(pdf_path: Path) -> dict:
    meta = json.loads(pdf_path.with_suffix(".meta.json").read_text(encoding="utf-8"))
    pages = []
    with pymupdf.open(pdf_path) as doc:
        for number, page in enumerate(doc, start=1):  # page numbers start at 1
            pages.append({"page": number, "text": page_to_text(page)})
    return {**meta, "pages": pages}


def main():
    for pdf_path in sorted(RAW_DIR.rglob("*.pdf")):
        result = extract_pdf(pdf_path)
        out_dir = PROCESSED_DIR / result["document_type"]
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{result['id']}.json"
        out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"{result['id']:<30} {len(result['pages'])} pages -> {out_path.name}")


if __name__ == "__main__":
    main()
