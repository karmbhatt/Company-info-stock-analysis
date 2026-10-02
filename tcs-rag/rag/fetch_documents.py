"""Download the TCS documents listed in the manifest.

Usage:
    python -m rag.fetch_documents                 # fetch everything with a URL
    python -m rag.fetch_documents --dry-run       # show what would happen
    python -m rag.fetch_documents --only tcs_results_q4_fy26
    python -m rag.fetch_documents --force         # re-download existing files

Each PDF is saved to data/raw/tcs/<document_type>/<id>.pdf with a sidecar
<id>.meta.json (source URL, hash, download time). The ingestion step later
reads this sidecar so every chunk can carry citation metadata.
"""
import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone

import requests
import yaml

from rag.config import MANIFEST_PATH, RAW_DIR

HEADERS = {
    # Some corporate sites reject the default python-requests agent.
    "User-Agent": "Mozilla/5.0 (compatible; tcs-rag-research/0.1)",
    "Accept": "application/pdf,*/*",
}
RETRIES = 3
TIMEOUT = 60


def load_manifest():
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["company"], data["documents"]


def download(url: str) -> bytes:
    last_err = None
    for attempt in range(1, RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.content
        except requests.RequestException as err:
            last_err = err
            time.sleep(2 * attempt)
    raise RuntimeError(f"download failed after {RETRIES} attempts: {last_err}")


def write_meta(meta_path, company: str, doc: dict, source_url: str, content: bytes):
    meta = {
        "company": company,
        **{k: v for k, v in doc.items() if k not in ("url", "source_page")},
        "source_url": source_url,
        "sha256": hashlib.sha256(content).hexdigest(),
        "bytes": len(content),
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def fetch_one(company: str, doc: dict, force: bool, dry_run: bool) -> str:
    doc_id = doc["id"]
    url = (doc.get("url") or "").strip()
    out_dir = RAW_DIR / doc["document_type"]
    pdf_path = out_dir / f"{doc_id}.pdf"
    meta_path = out_dir / f"{doc_id}.meta.json"

    if not url:
        # No download link: maybe the PDF was saved by hand into the right folder.
        if pdf_path.exists():
            if meta_path.exists() and not force:
                return "exists"
            if dry_run:
                return "would_register"
            content = pdf_path.read_bytes()
            if not content.startswith(b"%PDF"):
                raise RuntimeError("file is not a PDF")
            write_meta(meta_path, company, doc, doc.get("source_page", ""), content)
            return "registered"
        return "needs_url"

    if pdf_path.exists() and not force:
        return "exists"
    if dry_run:
        return "would_download"

    content = download(url)
    if not content.startswith(b"%PDF"):
        raise RuntimeError("response is not a PDF (blocked or wrong link?)")

    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(content)
    write_meta(meta_path, company, doc, url, content)
    return "downloaded"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--only", help="fetch a single document id")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    company, docs = load_manifest()
    if args.only:
        docs = [d for d in docs if d["id"] == args.only]
        if not docs:
            print(f"No document with id {args.only!r} in manifest")
            return 1

    failures = 0
    for doc in docs:
        try:
            status = fetch_one(company, doc, args.force, args.dry_run)
        except Exception as err:  # keep going; report at the end
            status = f"FAILED ({err})"
            failures += 1
        print(f"{doc['id']:<30} {status}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())