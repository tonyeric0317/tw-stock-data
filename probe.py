import re, ssl, urllib.request
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36", "Accept-Language": "zh-TW,zh;q=0.9"}
ctx = ssl._create_unverified_context()
urls = [
 "https://www.yuanta.com.tw/eYuanta/Securities/News/GetAPIList?Type=StockHotNews",
 "https://wantrich.chinatimes.com/newslist/420101/1",
 "https://wantrich.chinatimes.com/newslist/42/1",
 "https://www.chinatimes.com/realtimenews/260410/",
 "https://www.chinatimes.com/realtimenews/260410/?page=2",
 "https://wantrich.chinatimes.com/rss",
 "https://www.chinatimes.com/rss/realtimenews-finance.xml",
 "https://news.mtkstock.com.tw/",
]
for u in urls:
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30, context=ctx) as r:
            b = r.read().decode("utf-8", "replace")
        hits = re.findall(r"《熱門族群》[^<\"]{0,40}", b)
        times = re.findall(r"20\d\d[-/]\d\d[-/]\d\d[ T]?\d\d:\d\d", b)
        links = re.findall(r"(?:/news/|realtimenews/)\d{14}-\d+", b)
        print(f"\n### {u}\nlen {len(b)} 熱門族群 {len(hits)} {hits[:4]}\n times {times[:4]} links {links[:3]}")
    except Exception as e:
        print(f"\n### {u}\nERROR {e}")
