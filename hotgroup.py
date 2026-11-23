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
POOL = "data/hotgroup_pool.json"


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s or ""))).strip()


def main():
    now = dt.datetime.now(TW)
    pool = json.load(open(POOL, encoding="utf-8")) if os.path.exists(POOL) else {}
    status = "正常"
    try:
        with urllib.request.urlopen(urllib.request.Request(URL, headers=UA), timeout=30,
                                    context=ssl._create_unverified_context()) as r:
            b = r.read().decode("utf-8", "replace")
        items = re.findall(r"GetThisPageItem\('(\d+)'\).*?tag date\">\s*([\d/]+)\s*</span>\s*<span class=\"tag time\">\s*([\d:]+)\s*</span>\s*<p>(.*?)</p>", b, re.S)
        n = 0
        for nid, d, t, title in items:
            title = clean(title)
            if "熱門族群" in title and nid not in pool:
                pool[nid] = {"date": d.replace("/", "-"), "time": t, "title": title, "first_seen": now.isoformat(timespec="minutes")}
                n += 1
        status = f"正常（本次列表 {len(items)} 則，新增 {n} 篇）"
    except Exception as e:
        status = f"元大列表抓取失敗：{e}"

    cut = (now - dt.timedelta(days=10)).date().isoformat()
    pool = {k: v for k, v in pool.items() if v["date"] >= cut}
    os.makedirs("data", exist_ok=True)
    json.dump(pool, open(POOL, "w", encoding="utf-8"), ensure_ascii=False, indent=0)

    today = now.date().isoformat()
    rows = sorted((v["time"], v["title"]) for v in pool.values() if v["date"] == today)
    with open("data/latest_hotgroup.txt", "w", encoding="utf-8") as f:
        f.write(f"《熱門族群》標題清單｜日期 {today}｜更新時間 {now:%Y-%m-%d %H:%M}｜共 {len(rows)} 篇｜來源：元大證券熱門新聞列表（{status}）\n")
        f.write("\n".join(f"{t}｜{title}" for t, title in rows) if rows else "（今天尚未收集到《熱門族群》）")
        f.write("\n")
    print(open("data/latest_hotgroup.txt", encoding="utf-8").read())


if __name__ == "__main__":
    main()
