import json
from pathlib import Path

DIR = Path("data/processed/tcs")

for path in sorted(DIR.rglob("*.json")):
    doc = json.loads(path.read_text(encoding="utf-8"))
    print(f"\n{doc['id']}  ({len(doc['pages'])} pages)")
    for p in doc["pages"]:
        n = len(p["text"])
        flag = "  <-- almost empty!" if n < 200 else ""
        print(f"  page {p['page']:>2}: {n:>5} chars{flag}")

# Known-answer check: a line we already saw with our own eyes
q4 = json.loads((DIR / "quarterly_results/tcs_results_q4_fy26.json").read_text(encoding="utf-8"))
expected = "Revenue from operations 70,698 67,087 64,479 267,021 2,55,324"
page9 = q4["pages"][8]["text"]
print("\nKnown-answer check:", "PASS" if expected in page9 else "FAIL")
