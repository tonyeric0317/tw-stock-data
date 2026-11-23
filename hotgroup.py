#!/usr/bin/env python3
"""
收集時報資訊《熱門族群》專欄標題（來源：元大證券熱門新聞列表，轉載時報資訊）
每次執行累積到 data/hotgroup_pool.json（保留 10 天），輸出今天的清單 data/latest_hotgroup.txt
"""
import datetime as dt, html, json, os, re, ssl, urllib.request
from zoneinfo import ZoneInfo

TW = ZoneInfo("Asia/Taipei")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept-Language": "zh-TW,zh;q=0.9"}
URL = "https://www.yuanta.com.tw/eYuanta/Securities/News/GetAPIList?Type=StockHotNews"
ITEM = "https://www.yuanta.com.tw/eYuanta/Securities/News/GetAPItem?Type=StockHotNews&id={}"
POOL = "data/hotgroup_pool.json"


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s or ""))).strip()


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30,
                                context=ssl._create_unverified_context()) as r:
        return r.read().decode("utf-8", "replace")


def stocks_in(text):
    """找文中提到的上市櫃個股：先抓括號內代號，再用公司名比對"""
    names = {}
    try:
        import csv
        with open("data/latest_turnover.csv", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                names[r["代號"]] = r["名稱"].replace("*", "")
    except FileNotFoundError:
        pass
    codes = [c for c in re.findall(r"[（(](\d{4})[)）]", text) if c in names or not names]
    rest = text
    for c, n in sorted(names.items(), key=lambda t: -len(t[1])):
        if len(n) >= 2 and n in rest:
            codes.append(c)
            rest = rest.replace(n, "")
    return [(names.get(c, ""), c) for c in dict.fromkeys(codes)]


def main():
    now = dt.datetime.now(TW)
    pool = json.load(open(POOL, encoding="utf-8")) if os.path.exists(POOL) else {}
    status = "正常"
    try:
        b = fetch(URL)
        items = re.findall(r"GetThisPageItem\('(\d+)'\).*?tag date\">\s*([\d/]+)\s*</span>\s*<span class=\"tag time\">\s*([\d:]+)\s*</span>\s*<p>(.*?)</p>", b, re.S)
        n = 0
        for nid, d, t, title in items:
            title = clean(title)
            if "熱門族群" in title and nid not in pool:
                pool[nid] = {"date": d.replace("/", "-"), "time": t, "title": title, "url": ITEM.format(nid),
                             "first_seen": now.isoformat(timespec="minutes")}
                n += 1
        # 打開文章抓出提到的個股（每篇只抓一次）
        for nid, v in pool.items():
            if "stocks" in v:
                continue
            v.setdefault("url", ITEM.format(nid))
            try:
                raw = fetch(v["url"])
                m = re.search(r'<h5 class="tit">(.*?)class="btnArea"', raw, re.S)
                if not m:
                    raise ValueError("找不到文章內文區塊")
                v["stocks"] = stocks_in(clean(m.group(1)))
            except Exception as e:
                v["stocks_error"] = str(e)
        status = f"正常（本次列表 {len(items)} 則，新增 {n} 篇）"
    except Exception as e:
        status = f"元大列表抓取失敗：{e}"

    cut = (now - dt.timedelta(days=10)).date().isoformat()
    pool = {k: v for k, v in pool.items() if v["date"] >= cut}
    os.makedirs("data", exist_ok=True)
    json.dump(pool, open(POOL, "w", encoding="utf-8"), ensure_ascii=False, indent=0)

    today = now.date().isoformat()
    rows = sorted((v["time"], v["title"], v.get("url", ""), "、".join(f"{n} {c}" for n, c in v.get("stocks", [])) or "（未抓到個股）")
                  for v in pool.values() if v["date"] == today)
    with open("data/latest_hotgroup.txt", "w", encoding="utf-8") as f:
        f.write(f"《熱門族群》標題清單｜日期 {today}｜更新時間 {now:%Y-%m-%d %H:%M}｜共 {len(rows)} 篇｜來源：元大證券熱門新聞列表（{status}）\n")
        f.write("每行格式：發布時間｜標題｜元大全文網址｜文中提到的個股（程式比對，可能有漏或誤判）\n")
        f.write("\n".join(f"{t}｜{title}｜{u}｜{st}" for t, title, u, st in rows) if rows else "（今天尚未收集到《熱門族群》）")
        f.write("\n")
    print(open("data/latest_hotgroup.txt", encoding="utf-8").read())


if __name__ == "__main__":
    main()
