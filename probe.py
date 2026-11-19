import re, ssl, urllib.request
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept-Language": "zh-TW,zh;q=0.9"}
urls = [
 "https://money.udn.com/money/cate/5590",
 "https://money.udn.com/money/cate/5591",
 "https://money.udn.com/rssfeed/news/1001/5590?ch=money",
 "https://money.udn.com/rssfeed/news/1001/5591?ch=money",
 "https://money.udn.com/rssfeed/news/1001/5612?ch=money",
 "https://money.udn.com/rssfeed/news/1001/5710?ch=money",
 "https://money.udn.com/rssfeed/news/1001/11074?ch=money",
 "https://www.ctee.com.tw/stock/twmarket",
 "https://www.ctee.com.tw/livenews/stock",
 "https://www.ctee.com.tw/rss_web/livenews/stock",
 "https://www.ctee.com.tw/rss_web/livenews/ctee",
 "https://www.ctee.com.tw/sitemap_news.xml",
 "https://www.ctee.com.tw/news-sitemap.xml",
 "https://www.ctee.com.tw/sitemap.xml",
 "https://www.ctee.com.tw/robots.txt",
 "https://api.cnyes.com/media/api/v1/newslist/category/tw_stock_news?limit=30",
 "https://api.cnyes.com/media/api/v1/newslist/category/tw_stock?limit=30",
]
ctx = ssl._create_unverified_context()
for u in urls:
    try:
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
            b = r.read().decode("utf-8", "replace")
            print(f"\n### {u}\nstatus {r.status} len {len(b)} type {r.headers.get('Content-Type')}")
            print(re.sub(r"\s+", " ", b[:1500]))
            for pat in [r"/money/story/\d+/\d+", r"/news/\d{8}\d+-\d+", r"news/id/\d+", r"<loc>[^<]+</loc>", r"Sitemap:[^\n]+"]:
                m = re.findall(pat, b)
                if m: print("  MATCH", pat, len(m), m[:5])
            t = re.findall(r"20\d\d[-/]\d\d[-/]\d\d[ T]\d\d:\d\d", b)
            if t: print("  TIMES", len(t), t[:5])
    except Exception as e:
        print(f"\n### {u}\nERROR {e}")
