import fitz  # this is PyMuPDF's import name

PDF = "data/raw/tcs/quarterly_results/tcs_results_q4_fy26.pdf"

doc = fitz.open(PDF)
print("Total pages:", len(doc))

for page_number, page in enumerate(doc, start=1):
    text = page.get_text()
    if "Revenue from operations" in text:
        print(f"\n--- Found on page {page_number} ---")
        print(text[:1500])
        break
