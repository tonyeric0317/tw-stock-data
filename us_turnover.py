#!/usr/bin/env python3
"""
美股成交額排行（個股，排除 ETF）＋ 漲幅 ≥ 8% 篩選

資料來源：Nasdaq 官網的股票篩選器 API（涵蓋 NASDAQ、NYSE、AMEX 全部個股，收盤後資料）
成交額 = 最新價 × 成交量（美元）

用法：
  python us_turnover.py --date 20261118 --csv data/us_turnover_20261118.csv
"""
import argparse, csv, json, re, ssl, sys, urllib.error, urllib.request

URL = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=10000&download=true"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.nasdaq.com",
    "Referer": "https://www.nasdaq.com/",
}


def fetch():
    req = urllib.request.Request(URL, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.URLError as e:
        if "CERTIFICATE_VERIFY_FAILED" not in str(e):
            raise
        with urllib.request.urlopen(req, timeout=60, context=ssl._create_unverified_context()) as r:
            return json.loads(r.read().decode("utf-8"))


def num(s):
    s = re.sub(r"[$,%+]", "", str(s or "")).strip()
    try:
        return float(s)
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="美股交易日 YYYYMMDD（美東）")
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--min-pct", type=float, default=8.0)
    ap.add_argument("--csv", required=True)
    a = ap.parse_args()

    data = fetch()
    rows = data.get("data", {}).get("rows") or []
    if not rows:
        sys.exit("Nasdaq API 沒有回傳資料")

    out = []
    for r in rows:
        sym = (r.get("symbol") or "").strip()
        price, vol, pct = num(r.get("lastsale")), num(r.get("volume")), num(r.get("pctchange"))
        if not sym or price is None or vol is None:
            continue
        # 排除權證、優先股、單位等（代號含 ^ / 或名稱含 Warrant/Unit/Preferred）
        name = r.get("name") or ""
        if re.search(r"[\^/]", sym) or re.search(r"\b(Warrants?|Units?|Rights?|Preferred|Depositary Shares? representing)\b", name, re.I):
            continue
        out.append({"symbol": sym, "name": name, "price": price, "pct": pct,
                    "volume": int(vol), "turnover": price * vol,
                    "mcap": num(r.get("marketCap")), "sector": r.get("sector") or "", "industry": r.get("industry") or ""})

    out.sort(key=lambda x: x["turnover"], reverse=True)
    for i, x in enumerate(out, 1):
        x["rank"] = i
    top = out[: a.top]
    hits = [x for x in top if x["pct"] is not None and x["pct"] >= a.min_pct]

    print(f"美股交易日：{a.date[:4]}-{a.date[4:6]}-{a.date[6:]}（美東）")
    print(f"資料來源：Nasdaq 股票篩選器（NASDAQ／NYSE／AMEX 個股，不含 ETF），共 {len(out)} 檔")
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
        for x in out[:200]:
            w.writerow([x["rank"], x["symbol"], x["name"], x["price"], f"{x['pct']:.2f}" if x["pct"] is not None else "",
                        x["volume"], f"{x['turnover']/1e8:.2f}", f"{x['mcap']/1e8:.1f}" if x["mcap"] else "", x["industry"]])


if __name__ == "__main__":
    main()
