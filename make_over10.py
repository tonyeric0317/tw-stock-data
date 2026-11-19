"""從完整排行 CSV 另存兩個小檔：成交值前 100 名、成交值 ≥ 10 億的個股（給排程快速讀取）"""
import csv, sys
d = sys.argv[1]
rows = list(csv.reader(open(f"data/turnover_{d}.csv", encoding="utf-8-sig")))
head, body = rows[0], rows[1:]
for name, keep in ((f"data/top100_{d}.csv", body[:100]),
                   (f"data/over10_{d}.csv", [r for r in body if float(r[8]) >= 10])):
    with open(name, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(head)
        w.writerows(keep)
