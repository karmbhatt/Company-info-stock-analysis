import pymupdf

PDF = "data/raw/tcs/quarterly_results/tcs_results_q4_fy26.pdf"

doc = pymupdf.open(PDF)
page = doc[8]  # page 9; Python counts pages from 0

found = page.find_tables()
print("Tables found:", len(found.tables))

if found.tables:
    for row in found.tables[0].extract()[:12]:
        print(row)
