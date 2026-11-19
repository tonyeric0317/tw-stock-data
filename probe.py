import json, re, ssl, time, urllib.request
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept-Language": "zh-TW,zh;q=0.9"}
ctx = ssl._create_unverified_context()
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30, context=ctx) as r:
        return r.read().decode("utf-8", "replace")
for u in ["https://www.ctee.com.tw/sitemaps/sitemap_newstoday.xml"]:
    try:
        b = get(u); print("###", u, len(b)); print(b[:2500])
        print("LOC count", len(re.findall("<loc>", b)))
    except Exception as e: print("###", u, "ERROR", e)
now = int(time.time())
for u in [f"https://api.cnyes.com/media/api/v1/newslist/category/tw_stock?limit=100&startAt={now-86400}&endAt={now}",
          "https://api.cnyes.com/media/api/v1/newslist/category/tw_stock_news?limit=100&page=1"]:
    try:
        d = json.loads(get(u)); items = d["items"]
        print("###", u); print({k: items[k] for k in items if k != "data"})
        for it in items["data"][:5]:
            print({k: it.get(k) for k in ("newsId", "title", "publishAt", "categoryName", "keyword", "market")})
        print("count", len(items["data"]), "oldest", time.strftime("%m-%d %H:%M", time.gmtime(items["data"][-1]["publishAt"] + 8*3600)))
    except Exception as e: print("###", u, "ERROR", e)
