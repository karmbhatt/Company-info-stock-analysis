"""Cut the extracted pages into chunks, each carrying citation metadata.

Rules (kept deliberately simple for V1):
* A chunk never crosses a page boundary, so "page" in a citation is exact.
* Prose pages ("plain"): split into sentences, pack them up to MAX_CHARS, and
  repeat the tail of each chunk (OVERLAP_CHARS) at the start of the next one so an
  idea cut at the boundary still appears whole somewhere.
* Table pages ("rows"): split between rows, and repeat the page's header lines
  (title, units, column titles) at the top of EVERY chunk, so a chunk of rows
  still says which column is which period.

Output: data/processed/tcs/chunks.jsonl  (one JSON object per line)
"""
import json
import re

from rag.config import ROOT
from rag.extract import NUMBER, PROCESSED_DIR

MAX_CHARS = 1200        # prose chunk size (about 250 words)
OVERLAP_CHARS = 150
TABLE_MAX_CHARS = 1500  # table chunk size, header included
MIN_CHARS = 40          # drop near-empty chunks (cover pages, stray labels)
OUT_PATH = PROCESSED_DIR / "chunks.jsonl"

SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def split_long(sentence: str, max_chars: int) -> list[str]:
    """Break a sentence with no full stop (a list, a heading run) at word boundaries."""
    parts, current = [], ""
    for word in sentence.split():
        if current and len(current) + 1 + len(word) > max_chars:
            parts.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        parts.append(current)
    return parts


def prose_chunks(text: str) -> list[str]:
    flat = " ".join(text.split())                     # collapse line breaks and spaces
    units = []
    for sentence in SENTENCE_END.split(flat):
        units.extend(split_long(sentence, MAX_CHARS) if len(sentence) > MAX_CHARS else [sentence])

    chunks, current = [], []
    for unit in units:
        if current and len(" ".join(current)) + 1 + len(unit) > MAX_CHARS:
            chunks.append(" ".join(current))
            tail = []                                  # carry the last sentences over
            for s in reversed(current):
                if sum(len(x) + 1 for x in tail) + len(s) > OVERLAP_CHARS:
                    break
                tail.insert(0, s)
            current = tail
        current.append(unit)
    if current:
        chunks.append(" ".join(current))
    return chunks


def numeric_count(line: str) -> int:
    return sum(bool(NUMBER.match(tok)) for tok in line.split())


def table_chunks(text: str) -> list[str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    # the header is everything above the first row that has at least 3 figures
    first = next((i for i, ln in enumerate(lines) if numeric_count(ln) >= 3), None)
    header, body = (lines[:first], lines[first:]) if first is not None else ([], lines)
    header = header[-8:]                               # keep it short
    head_text = "\n".join(header)

    chunks, current, size = [], [], len(head_text)
    for line in body:
        if current and size + len(line) + 1 > TABLE_MAX_CHARS:
            chunks.append("\n".join(header + current))
            current, size = [], len(head_text)
        current.append(line)
        size += len(line) + 1
    if current:
        chunks.append("\n".join(header + current))
    return chunks


def chunk_document(doc: dict) -> list[dict]:
    out = []
    for page in doc["pages"]:
        pieces = table_chunks(page["text"]) if page["method"] == "rows" else prose_chunks(page["text"])
        for i, piece in enumerate(pieces):
            if len(piece) < MIN_CHARS:
                continue
            out.append({
                "chunk_id": f"{doc['id']}_p{page['page']}_{i}",
                "company": doc["company"],
                "document_id": doc["id"],
                "document_type": doc["document_type"],
                "fiscal_year": doc.get("fiscal_year"),
                "period": doc.get("period"),
                "title": doc["title"],
                "source_url": doc["source_url"],
                "page": page["page"],
                "method": page["method"],
                "text": piece,
            })
    return out


def main():
    total = 0
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for path in sorted(PROCESSED_DIR.rglob("*.json")):
            doc = json.loads(path.read_text(encoding="utf-8"))
            chunks = chunk_document(doc)
            for c in chunks:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
            sizes = [len(c["text"]) for c in chunks]
            avg = sum(sizes) // max(len(sizes), 1)
            print(f"{doc['id']:<30} {len(chunks):>5} chunks   avg {avg} chars   max {max(sizes, default=0)}")
            total += len(chunks)
    print(f"\n{total} chunks -> {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()