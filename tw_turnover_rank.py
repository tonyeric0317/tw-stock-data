#!/usr/bin/env python3
"""
台股成交值排行（上市＋上櫃合併）＋ 漲停股篩選

資料來源：證交所與櫃買中心的官方收盤行情（收盤後的正式資料）
  - 上市：證交所「每日收盤行情」(MI_INDEX)，可指定日期
  - 上櫃：櫃買中心「上櫃股票每日收盤行情」，可指定日期
  - 若上面抓不到，退回 OpenAPI（OpenAPI 通常比較晚才更新到當天）

用法：
  python3 tw_turnover_rank.py                 # 今天（台灣時間）的前100名＋漲停股
  python3 tw_turnover_rank.py --date 20261113 # 指定日期
  python3 tw_turnover_rank.py --top 200       # 改看前200名

只用 Python 內建模組，不需要另外安裝套件。
官方收盤行情大約 14:30～15:00 後才會有當天資料。
"""

import argparse
import csv
import datetime as dt
import json
import math
import re
import sys
import ssl
import urllib.error
import urllib.request

HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
TW = dt.timezone(dt.timedelta(hours=8))


def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8-sig"))
    except urllib.error.URLError as e:
        # 部分環境（例如 GitHub Actions）缺證交所憑證鏈，只對公開行情資料改用不驗證憑證重試
        if "CERTIFICATE_VERIFY_FAILED" not in str(e):
            raise
        ctx = ssl._create_unverified_context()
        with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
            return json.loads(r.read().decode("utf-8-sig"))


def num(x):
    if x is None:
        return None
    s = re.sub(r"<[^>]+>", "", str(x)).replace(",", "").replace("+", "").strip()
    if s in ("", "--", "---", "X0.00"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def tick_size(price):
    if price < 10:
        return 0.01
    if price < 50:
        return 0.05
    if price < 100:
        return 0.1
    if price < 500:
        return 0.5
    if price < 1000:
        return 1.0
    return 5.0


def limit_up_price(prev_close):
    raw = prev_close * 1.10
    t = tick_size(raw)
    return round(math.floor(raw / t + 1e-9) * t, 2)


def is_regular_stock(code):
    return len(code) == 4 and code.isdigit() and not code.startswith("00")


def make_row(market, code, name, close, change, high, shares, value):
    if not code or close is None or value is None:
        return None
    prev = close - change if change is not None else None
    pct = (change / prev * 100) if (change is not None and prev) else None
    lu = bool(prev and change is not None and change > 0 and close >= limit_up_price(prev) - 1e-9)
    return {
        "market": market, "code": code, "name": name, "close": close,
        "change": change, "pct": pct, "high": high,
        "volume_lots": round(shares / 1000) if shares else None,
        "value_100m": value / 1e8, "limit_up": lu,
    }


# ---------- 上市 ----------
def twse_by_date(d):
    url = ("https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?"
           f"date={d:%Y%m%d}&type=ALLBUT0999&response=json")
    j = fetch_json(url)
    if j.get("stat") not in (None, "OK"):
        raise RuntimeError(f"證交所回應：{j.get('stat')}")
    tables = j.get("tables") or []
    # 舊格式相容
    for k in list(j.keys()):
        if k.startswith("fields") and k[6:]:
            tables.append({"fields": j[k], "data": j.get("data" + k[6:], [])})
    for t in tables:
        f = t.get("fields") or []
        if "證券代號" in f and "成交金額" in f and "收盤價" in f:
            ix = {name: i for i, name in enumerate(f)}
            out = []
            for r in t.get("data", []):
                sign = re.sub(r"<[^>]+>", "", str(r[ix["漲跌(+/-)"]])).strip() if "漲跌(+/-)" in ix else ""
                diff = num(r[ix["漲跌價差"]]) if "漲跌價差" in ix else None
                change = None if diff is None else (-diff if sign == "-" else diff)
                row = make_row("上市", str(r[ix["證券代號"]]).strip(), str(r[ix["證券名稱"]]).strip(),
                               num(r[ix["收盤價"]]), change, num(r[ix["最高價"]]),
                               num(r[ix["成交股數"]]), num(r[ix["成交金額"]]))
                if row:
                    out.append(row)
            if out:
                return out, tpex_actual_date(j, d)
    raise RuntimeError("證交所當天沒有收盤行情（可能還沒更新或休市）")


def twse_openapi():
    rows = fetch_json("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL")
    out, date = [], None
    for r in rows:
        date = date or r.get("Date")
        row = make_row("上市", str(r.get("Code", "")).strip(), str(r.get("Name", "")).strip(),
                       num(r.get("ClosingPrice")), num(r.get("Change")), num(r.get("HighestPrice")),
                       num(r.get("TradeVolume")), num(r.get("TradeValue")))
        if row:
            out.append(row)
    return out, f"{date}（OpenAPI，民國年）"


# ---------- 上櫃 ----------
def tpex_actual_date(j, d):
    """讀回櫃買中心回傳的實際資料日期；沒有日期欄位才用查詢日期"""
    raw = str(j.get("date") or j.get("reportDate") or "").strip()
    m = re.match(r"(\d{2,4})[/-]?(\d{2})[/-]?(\d{2})$", raw)
    if not m:
        return f"{d:%Y%m%d}"
    y = int(m.group(1))
    y = y + 1911 if y < 1911 else y
    return f"{y}{m.group(2)}{m.group(3)}"


def tpex_by_date(d):
    roc = f"{d.year - 1911}/{d:%m/%d}"
    urls = [
        f"https://www.tpex.org.tw/www/zh-tw/afterTrading/dailyQuotes?date={d:%Y}%2F{d:%m}%2F{d:%d}&type=EW&response=json",
        f"https://www.tpex.org.tw/web/stock/aftertrading/daily_close_quotes/stk_quote_result.php?l=zh-tw&d={roc}&o=json",
    ]
    last_err = None
    for url in urls:
        try:
            j = fetch_json(url)
        except Exception as e:
            last_err = e
            continue
        candidates = []
        for t in j.get("tables") or []:
            candidates.append((t.get("fields") or [], t.get("data") or []))
        if j.get("aaData"):
            candidates.append(([], j["aaData"]))
        for fields, data in candidates:
            if not data:
                continue
            ix = {name.strip(): i for i, name in enumerate(fields)}

            def col(r, names, pos):
                for n in names:
                    if n in ix:
                        return r[ix[n]]
                return r[pos] if len(r) > pos else None

            out = []
            for r in data:
                row = make_row("上櫃", str(col(r, ["代號"], 0)).strip(), str(col(r, ["名稱"], 1)).strip(),
                               num(col(r, ["收盤"], 2)), num(col(r, ["漲跌"], 3)), num(col(r, ["最高"], 5)),
                               num(col(r, ["成交股數"], 8)), num(col(r, ["成交金額(元)", "成交金額"], 9)))
                if row:
                    out.append(row)
            if out:
                return out, tpex_actual_date(j, d)
    raise RuntimeError(f"櫃買中心當天沒有收盤行情（可能還沒更新或休市）{last_err or ''}")


def tpex_openapi():
    rows = fetch_json("https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes")
    out, date = [], None
    for r in rows:
        date = date or r.get("Date")
        row = make_row("上櫃", str(r.get("SecuritiesCompanyCode", "")).strip(), str(r.get("CompanyName", "")).strip(),
                       num(r.get("Close")), num(r.get("Change")), num(r.get("High")),
                       num(r.get("TradingShares")), num(r.get("TransactionAmount")))
        if row:
            out.append(row)
    return out, f"{date}（OpenAPI，民國年）"


def get(fn_date, fn_api, d, label):
    try:
        return fn_date(d)
    except Exception as e:
        print(f"⚠️ {label}指定日期資料抓不到：{e}，改用 OpenAPI")
        try:
            return fn_api()
        except Exception as e2:
            print(f"⚠️ {label} OpenAPI 也失敗：{e2}")
            return [], None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYYMMDD，預設今天（台灣時間）")
    ap.add_argument("--top", type=int, default=100)
    ap.add_argument("--keep-etf", action="store_true")
    ap.add_argument("--csv", default=None)
    args = ap.parse_args()

    d = dt.datetime.strptime(args.date, "%Y%m%d").date() if args.date else dt.datetime.now(TW).date()

    twse_rows, twse_date = get(twse_by_date, twse_openapi, d, "上市")
    tpex_rows, tpex_date = get(tpex_by_date, tpex_openapi, d, "上櫃")
    if not twse_rows and not tpex_rows:
        sys.exit("上市、上櫃資料都抓不到")

    rows = twse_rows + tpex_rows
    if not args.keep_etf:
        rows = [r for r in rows if is_regular_stock(r["code"])]
    rows.sort(key=lambda r: r["value_100m"], reverse=True)
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    top = rows[: args.top]

    print(f"查詢日期：{d:%Y-%m-%d}")
    print(f"實際資料日期：上市 {twse_date}／上櫃 {tpex_date}")
    if str(twse_date) != f"{d:%Y%m%d}" or str(tpex_date) != f"{d:%Y%m%d}":
        print("⚠️ 資料日期與查詢日期不同（可能官方尚未更新或今天休市）")
    print(f"成交值第 {len(top)} 名門檻：{top[-1]['value_100m']:.2f} 億\n")

    lu = [r for r in top if r["limit_up"]]
    note = ""
    if len(lu) > 10:
        lu = [r for r in lu if r["rank"] <= 50]
        note = "（漲停超過 10 檔，只列前 50 名內）"
    print(f"=== 成交值前 {args.top} 名中的漲停股 {note}===")
    if not lu:
        print(f"今日成交值前 {args.top} 名無漲停股")
    for r in lu:
        print(f"#{r['rank']:>3} {r['name']} {r['code']}（{r['market']}） "
              f"收 {r['close']:g}  +{r['pct']:.2f}%  "
              f"成交值 {r['value_100m']:.2f} 億  成交量 {r['volume_lots']:,} 張")

    fname = args.csv or f"turnover_{d:%Y%m%d}.csv"
    with open(fname, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["名次", "市場", "代號", "名稱", "收盤", "漲跌", "漲跌幅%", "成交量(張)", "成交值(億)", "漲停"])
        for r in rows:  # 存全部個股（含名次），方便核對任一檔的成交值、成交量、是否漲停
            w.writerow([r["rank"], r["market"], r["code"], r["name"], r["close"], r["change"],
                        f"{r['pct']:.2f}" if r["pct"] is not None else "",
                        r["volume_lots"], f"{r['value_100m']:.2f}", "是" if r["limit_up"] else ""])
    print(f"\n完整排行已存成：{fname}")


if __name__ == "__main__":
    main()
