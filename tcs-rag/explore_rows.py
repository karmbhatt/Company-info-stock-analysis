import pymupdf

PDF = "data/raw/tcs/quarterly_results/tcs_results_q4_fy26.pdf"
page = pymupdf.open(PDF)[8]  # page 9

# Each word: (x0, y0, x1, y1, text, ...). Sort top to bottom by vertical centre.
words = sorted(page.get_text("words"), key=lambda w: (w[1] + w[3]) / 2)

rows = []
for w in words:
    y_centre = (w[1] + w[3]) / 2
    if rows and abs(y_centre - rows[-1]["y"]) < 3:   # within 3 points = same row
        rows[-1]["words"].append(w)
    else:
        rows.append({"y": y_centre, "words": [w]})

for row in rows[:45]:
    left_to_right = sorted(row["words"], key=lambda w: w[0])
    print(" ".join(w[4] for w in left_to_right))
