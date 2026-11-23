import re, ssl, urllib.request
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
b = urllib.request.urlopen(urllib.request.Request("https://www.yuanta.com.tw/eYuanta/Securities/News/GetAPItem?Type=StockHotNews&id=202611230111309", headers=UA), timeout=30, context=ssl._create_unverified_context()).read().decode("utf-8","replace")
i = b.find("無懼美光")
print("LEN", len(b), "TITLEPOS", i)
for m in re.finditer("無懼美光", b): print("AT", m.start(), re.sub(r"\s+"," ",b[m.start()-400:m.start()+150]))
j = b.find("沈培華"); print("END", j, re.sub(r"\s+"," ",b[j-300:j+400]))
for w in ["元大金","統一","資通","嘉實"]:
    k=b.find(w); print(w, k, re.sub(r"\s+"," ",b[k-150:k+60]))
