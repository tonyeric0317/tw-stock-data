#!/usr/bin/env python3
"""
美股成交額排行（個股，排除 ETF）＋ 漲幅 ≥ 8% 篩選
資料來源：TradingView 公開篩選器（收盤後即為當日收盤資料；成交額＝Value.Traded，美元）
用法：python us_turnover.py --date 20261120 --csv data/us_top200_20261120.csv
"""
import argparse, csv, json, ssl, sys, urllib.error, urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
COLS = ["name", "description", "close", "change", "volume", "Value.Traded", "market_cap_basic", "sector", "industry", "type", "subtype"]


def fetch(n):
    body = json.dumps({
        "filter": [{"left": "type", "operation": "equal", "right": "stock"},
                   {"left": "is_primary", "operation": "equal", "right": True},
                   {"left": "subtype", "operation": "nin", "right": ["preferred", "warrant", "unit", "right"]}],
        "markets": ["america"], "columns": COLS,
        "sort": {"sortBy": "Value.Traded", "sortOrder": "desc"}, "range": [0, n]}).encode()
    req = urllib.request.Request("https://scanner.tradingview.com/america/scan", data=body,
                                 headers={"User-Agent": UA, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.URLError as e:
        if "CERTIFICATE_VERIFY_FAILED" not in str(e):
            raise
        with urllib.request.urlopen(req, timeout=60, context=ssl._create_unverified_context()) as r:
            return json.loads(r.read().decode())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="美股交易日 YYYYMMDD（美東）")
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--min-pct", type=float, default=8.0)
    ap.add_argument("--csv", required=True)
    a = ap.parse_args()

    rows = fetch(200).get("data") or []
    if not rows:
        sys.exit("TradingView 沒有回傳資料")
    out = []
    for i, r in enumerate(rows, 1):
        d = dict(zip(COLS, r["d"]))
        out.append({"rank": i, "symbol": d["name"], "name": d["description"] or "", "price": d["close"],
                    "pct": d["change"], "volume": d["volume"] or 0, "turnover": d["Value.Traded"] or 0,
                    "mcap": d["market_cap_basic"], "industry": d["industry"] or d["sector"] or ""})
    top = out[: a.top]
    hits = [x for x in top if x["pct"] is not None and x["pct"] >= a.min_pct]

    print(f"美股交易日：{a.date[:4]}-{a.date[4:6]}-{a.date[6:]}（美東）")
    print(f"資料來源：TradingView 篩選器（美股個股，不含 ETF、優先股、權證），成交額＝當日成交金額")
    print("核對用：成交額前 5 名 " + "、".join(f"{x['symbol']} {x['price']:g}（{x['pct']:+.2f}%）" for x in top[:5]))
    print(f"成交額第 {len(top)} 名門檻：{top[-1]['turnover']/1e8:.2f} 億美元\n")
    print(f"=== 成交額前 {a.top} 名中漲幅 ≥ {a.min_pct:g}% 的個股 ===")
    if not hits:
        print(f"成交額前 {a.top} 名無漲幅 {a.min_pct:g}% 以上個股")
    for x in hits:
        print(f"#{x['rank']:>2} {x['symbol']} {x['name']}  收 {x['price']:g}  {x['pct']:+.2f}%  "
              f"成交額 {x['turnover']/1e8:.2f} 億美元  產業 {x['industry']}")

    with open(a.csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["名次", "代號", "名稱", "收盤", "漲跌幅%", "成交量", "成交額(億美元)", "市值(億美元)", "產業"])
        for x in out:
            w.writerow([x["rank"], x["symbol"], x["name"], x["price"], f"{x['pct']:.2f}", int(x["volume"]),
                        f"{x['turnover']/1e8:.2f}", f"{x['mcap']/1e8:.1f}" if x["mcap"] else "", x["industry"]])


if __name__ == "__main__":
    main()
