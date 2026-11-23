import json, re, ssl, urllib.request
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36", "Accept-Language": "zh-TW,zh;q=0.9"}
ctx = ssl._create_unverified_context()
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30, context=ctx) as r:
        return r.read().decode("utf-8", "replace")
b = get("https://www.yuanta.com.tw/eYuanta/Securities/News/GetAPIList?Type=StockHotNews")
print(b[:600])
try:
    d = json.loads(b)
    print(type(d), (list(d.keys()) if isinstance(d, dict) else len(d)))
except Exception as e:
    print("not json", e)
for m in re.finditer(r"《熱門族群》", b):
    print("CTX", re.sub(r"\s+", " ", b[max(0, m.start()-300): m.start()+200]))
    break
print("total items approx", len(re.findall(r"20\d\d-\d\d-\d\d \d\d:\d\d", b)))
for u in ["https://wantrich.chinatimes.com/newslist/420101/2", "https://wantrich.chinatimes.com/newslist/420101/3"]:
    s = get(u); print(u, len(re.findall("熱門族群", s)), re.findall(r"/news/(\d{8})\d+-420101", s)[:3], re.findall(r"/news/(\d{8})\d+-420101", s)[-2:])
