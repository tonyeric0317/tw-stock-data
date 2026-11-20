import json, re, ssl, urllib.request
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json, text/plain, */*", "Origin": "https://www.nasdaq.com", "Referer": "https://www.nasdaq.com/"}
ctx = ssl._create_unverified_context()
def get(u, data=None, h=UA):
    r = urllib.request.Request(u, data=data, headers=h)
    with urllib.request.urlopen(r, timeout=40, context=ctx) as x: return x.read().decode("utf-8","replace")
print("### nasdaq marketmovers")
try:
    d = json.loads(get("https://api.nasdaq.com/api/marketmovers?assetclass=stocks&exchangestatus=currentMarket&limit=10"))
    s = json.dumps(d, ensure_ascii=False); print(s[:2500])
except Exception as e: print("ERR", e)
print("### tradingview scanner")
try:
    body = json.dumps({"filter":[{"left":"type","operation":"equal","right":"stock"},{"left":"is_primary","operation":"equal","right":True}],
        "markets":["america"],"columns":["name","description","close","change","volume","Value.Traded","market_cap_basic","exchange"],
        "sort":{"sortBy":"Value.Traded","sortOrder":"desc"},"range":[0,10]}).encode()
    d = json.loads(get("https://scanner.tradingview.com/america/scan", body, {"User-Agent": UA["User-Agent"], "Content-Type":"application/json"}))
    print(d.get("totalCount")); [print(x["s"], x["d"]) for x in d["data"]]
except Exception as e: print("ERR", e)
print("### futu html")
try:
    b = get("https://www.futunn.com/hk/quote/us/stock-list/all-us-stocks/top-turnover", h={"User-Agent": UA["User-Agent"], "Accept-Language":"zh-TW"})
    print(len(b)); i=b.find("NVDA"); print(re.sub(r"\s+"," ",b[max(0,i-1500):i+1500]))
except Exception as e: print("ERR", e)
