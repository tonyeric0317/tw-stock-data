#!/usr/bin/env python3
"""
晨報候選新聞收集：經濟日報（證券、產業）、工商時報、鉅亨網台股
- 每 30 分鐘跑一次，把新抓到的新聞累積到 data/news_pool.json（保留 4 天）
- 輸出前一交易日 13:30 之後、提到上市櫃公司的新聞，分成數個小檔：
  data/news_part1.txt ～ news_part8.txt（固定檔名，排程用固定網址讀）
"""
import csv, datetime as dt, html, json, os, re, ssl, time, urllib.request
from email.utils import parsedate_to_datetime

TW = dt.timezone(dt.timedelta(hours=8))
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept-Language": "zh-TW,zh;q=0.9"}
CTX = ssl._create_unverified_context()
POOL = "data/news_pool.json"
PARTS, PER_PART = 8, 40


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30, context=CTX) as r:
        return r.read().decode("utf-8", "replace")


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s or ""))).strip()


def rss(url, source):
    out = []
    for item in re.findall(r"<item>(.*?)</item>", get(url), re.S):
        title = clean(re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", (re.search(r"<title>(.*?)</title>", item, re.S) or [None, ""])[1], flags=re.S))
        link = clean(re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", (re.search(r"<link>(.*?)</link>", item, re.S) or [None, ""])[1], flags=re.S))
        pub = re.search(r"<pubDate>(.*?)</pubDate>", item, re.S)
        t = None
        try:
            t = parsedate_to_datetime(clean(pub.group(1))).astimezone(TW) if pub else None
        except Exception:
            pass
        if t is None:
            iso = re.search(r"(20\d\d-\d\d-\d\d)[T ](\d\d:\d\d(?::\d\d)?)([+-]\d\d:?\d\d|Z)?", item)
            if iso:
                tz = (iso.group(3) or "+08:00").replace("Z", "+00:00")
                if len(tz) == 5:
                    tz = tz[:3] + ":" + tz[3:]
                t = dt.datetime.fromisoformat(f"{iso.group(1)}T{iso.group(2)}{tz}").astimezone(TW)
        if title and link:
            out.append({"source": source, "title": title, "url": link.split("?")[0], "time": t.isoformat() if t else None})
    return out


def udn_page(url, source):
    b = get(url)
    out, seen = [], set()
    for m in re.finditer(r'href="(https://money\.udn\.com/money/story/\d+/\d+)[^"]*"[^>]*>(.*?)</a>', b, re.S):
        link, title = m.group(1), clean(m.group(2))
        if link in seen or len(title) < 6:
            continue
        seen.add(link)
        near = b[m.end(): m.end() + 800]
        tm = re.search(r"(20\d\d-\d\d-\d\d)[ T](\d\d:\d\d)", near)
        t = dt.datetime.fromisoformat(f"{tm.group(1)}T{tm.group(2)}").replace(tzinfo=TW) if tm else None
        out.append({"source": source, "title": title, "url": link, "time": t.isoformat() if t else None})
    return out


def cnyes(start, end):
    out, page = [], 1
    while page <= 10:
        d = json.loads(get(f"https://api.cnyes.com/media/api/v1/newslist/category/tw_stock?limit=30&page={page}&startAt={start}&endAt={end}"))["items"]
        for it in d["data"]:
            codes = [m["code"] for m in (it.get("market") or []) if str(m.get("symbol", "")).startswith("TWS:")]
            out.append({"source": "鉅亨網", "title": clean(it["title"]),
                        "url": f"https://news.cnyes.com/news/id/{it['newsId']}",
                        "time": dt.datetime.fromtimestamp(it["publishAt"], TW).isoformat(), "codes": codes})
        if d.get("current_page", 1) >= d.get("last_page", 1):
            break
        page += 1
    return out


def load_stocks():
    """代號→(名稱, 成交值)；用前一份官方收盤資料"""
    m = {}
    try:
        with open("data/latest_turnover.csv", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                m[r["代號"]] = (r["名稱"].replace("*", ""), r["成交值(億)"])
    except FileNotFoundError:
        pass
    return m


def prev_trading_close(now):
    d = now.date() - dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    if now.weekday() < 5 and now.time() >= dt.time(13, 30):
        d = now.date()
    return dt.datetime.combine(d, dt.time(13, 30), TW)


def main():
    now = dt.datetime.now(TW)
    pool = {}
    if os.path.exists(POOL):
        pool = {x["url"]: x for x in json.load(open(POOL, encoding="utf-8"))}

    fetched, log = [], []
    jobs = [
        ("經濟日報", lambda: rss("https://money.udn.com/rssfeed/news/1001/5590?ch=money", "經濟日報")),
        ("經濟日報", lambda: rss("https://money.udn.com/rssfeed/news/1001/5591?ch=money", "經濟日報")),
        ("經濟日報", lambda: udn_page("https://money.udn.com/money/cate/5590", "經濟日報")),
        ("經濟日報", lambda: udn_page("https://money.udn.com/money/cate/5591", "經濟日報")),
        ("工商時報", lambda: rss("https://www.ctee.com.tw/rss_web/livenews/stock", "工商時報")),
        ("工商時報", lambda: rss("https://www.ctee.com.tw/rss_web/livenews/ctee", "工商時報")),
        ("工商時報", lambda: rss("https://www.ctee.com.tw/rss_web/livenews/industry", "工商時報")),
        ("鉅亨網", lambda: cnyes(int(time.time()) - 3 * 86400, int(time.time()))),
    ]
    for name, fn in jobs:
        try:
            items = fn()
            fetched += items
            log.append(f"{name} {len(items)}")
        except Exception as e:
            log.append(f"{name} 失敗：{e}")

    for x in fetched:
        old = pool.get(x["url"])
        if old:
            if not old.get("time") and x.get("time"):
                old["time"] = x["time"]
            if x.get("codes"):
                old["codes"] = x["codes"]
            continue
        x["first_seen"] = now.isoformat(timespec="minutes")
        pool[x["url"]] = x

    cutoff = now - dt.timedelta(days=4)
    keep = [x for x in pool.values() if dt.datetime.fromisoformat(x.get("time") or x["first_seen"]) >= cutoff]
    os.makedirs("data", exist_ok=True)
    json.dump(sorted(keep, key=lambda x: x.get("time") or x["first_seen"]), open(POOL, "w", encoding="utf-8"), ensure_ascii=False, indent=0)

    # 輸出候選清單
    stocks = load_stocks()
    names = sorted(((n, c) for c, (n, _) in stocks.items() if len(n) >= 2), key=lambda t: -len(t[0]))
    start = prev_trading_close(now)
    rows = []
    for x in keep:
        t = dt.datetime.fromisoformat(x.get("time") or x["first_seen"])
        if t < start or t > now:
            continue
        codes = list(dict.fromkeys(x.get("codes") or []))
        codes += [c for c in re.findall(r"[（(](\d{4})[)）]", x["title"]) if c in stocks]
        title_left = x["title"]
        for n, c in names:
            if n in title_left:
                codes.append(c)
                title_left = title_left.replace(n, "")
        codes = [c for c in dict.fromkeys(codes) if c in stocks]
        if not codes:
            continue
        tag = "、".join(f"{stocks[c][0]} {c}（前日成交值 {stocks[c][1]} 億）" for c in codes[:4])
        rows.append((t, f"{t:%m/%d %H:%M}｜{x['source']}｜{x['title']}｜{tag}｜{x['url']}"))
    rows.sort()
    lines = [r for _, r in rows]
    header = (f"晨報候選新聞（台灣時間 {start:%m/%d %H:%M} ～ {now:%m/%d %H:%M}，只列標題提到上市櫃公司的新聞）"
              f" 共 {len(lines)} 則，分 {PARTS} 個檔案，每檔最多 {PER_PART} 則。抓取狀況：{'；'.join(log)}")
    for i in range(PARTS):
        chunk = lines[i * PER_PART:(i + 1) * PER_PART]
        with open(f"data/news_part{i + 1}.txt", "w", encoding="utf-8") as f:
            f.write(header + f"\n【第 {i + 1} 檔】\n" + ("\n".join(chunk) if chunk else "（本檔沒有新聞）") + "\n")
    if len(lines) > PARTS * PER_PART:
        print(f"⚠️ 新聞 {len(lines)} 則超過容量，最舊的部分未輸出")
    print(header)


if __name__ == "__main__":
    main()
