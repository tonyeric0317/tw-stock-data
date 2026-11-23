#!/usr/bin/env python3
"""
每次被觸發（建議每 15～30 分鐘）就檢查該做什麼：
1. 新聞收集：每次都跑
2. 台股收盤資料：最近一個已收盤交易日（平日 15:30 後算當天），若還沒抓到才跑（官方未更新就下次再試）
3. 美股收盤資料：最近一個已收盤的美股交易日，若還沒抓到才跑
排程時間不準也沒關係：日期一律依「實際時間」推算，不會把盤中資料標成收盤。
"""
import datetime as dt, glob, os, re, shutil, subprocess, sys
from zoneinfo import ZoneInfo

TW, ET = ZoneInfo("Asia/Taipei"), ZoneInfo("America/New_York")


def run(cmd, out=None):
    print("$", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(r.stdout[-3000:], r.stderr[-2000:], flush=True)
    if out:
        open(out, "w", encoding="utf-8").write(r.stdout)
    return r.returncode == 0, r.stdout


def prev_weekday(d):
    d -= dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def tw_job(now):
    # 目標：最近一個已收盤的台股交易日（平日 15:30 後算當天，否則算前一個平日）
    d = now.date()
    if now.weekday() >= 5 or now.time() < dt.time(15, 30):
        d = prev_weekday(d) if now.weekday() < 5 else d
        while d.weekday() >= 5:
            d -= dt.timedelta(days=1)
    D = d.strftime("%Y%m%d")
    if os.path.exists(f"data/summary_{D}.txt"):
        return print(f"台股：{D} 已有資料")
    ok, out = run([sys.executable, "tw_turnover_rank.py", "--date", D, "--csv", f"data/turnover_{D}.csv"], f"data/summary_{D}.txt")
    if not ok or "資料日期與查詢日期不同" in out or "抓不到" in out:
        for f in glob.glob(f"data/*_{D}.*"):
            os.remove(f)
        return print("台股：官方資料尚未更新，下次再試")
    run([sys.executable, "make_over10.py", D])
    for a, b in [("summary", "txt"), ("over10", "csv"), ("over5", "csv"), ("top100", "csv"), ("turnover", "csv"), ("limitup", "csv")]:
        shutil.copy(f"data/{a}_{D}.{b}", f"data/latest_{a}.{b}")
    print(f"台股：{D} 更新完成")


def us_job(now_et):
    d = now_et.date()
    if now_et.weekday() >= 5 or now_et.time() < dt.time(16, 10):
        d = prev_weekday(d) if not (now_et.weekday() >= 5) else d
        while d.weekday() >= 5:
            d -= dt.timedelta(days=1)
    if now_et.weekday() < 5 and dt.time(9, 25) <= now_et.time() < dt.time(16, 10):
        return print("美股：盤中，略過")
    D = d.strftime("%Y%m%d")
    if os.path.exists(f"data/us_summary_{D}.txt"):
        return print(f"美股：{D} 已有資料")
    ok, _ = run([sys.executable, "us_turnover.py", "--date", D, "--csv", f"data/us_top200_{D}.csv"], f"data/us_summary_{D}.txt")
    if not ok:
        for f in glob.glob(f"data/us_*_{D}.*"):
            os.remove(f)
        return print("美股：抓取失敗，下次再試")
    shutil.copy(f"data/us_summary_{D}.txt", "data/latest_us_summary.txt")
    shutil.copy(f"data/us_top200_{D}.csv", "data/latest_us_top200.csv")
    print(f"美股：{D} 更新完成")


def cleanup(now):
    cut = (now - dt.timedelta(days=60)).strftime("%Y%m%d")
    for f in glob.glob("data/*_2*.*"):
        m = re.search(r"_(\d{8})\.", f)
        if m and m.group(1) < cut:
            os.remove(f)


def main():
    os.makedirs("data", exist_ok=True)
    now = dt.datetime.now(TW)
    print("台灣時間", now, "／美東時間", now.astimezone(ET))
    for name, fn in [("台股", lambda: tw_job(now)), ("美股", lambda: us_job(now.astimezone(ET))),
                     ("新聞", lambda: run([sys.executable, "news.py"])),
                     ("熱門族群", lambda: run([sys.executable, "hotgroup.py"])), ("清理", lambda: cleanup(now))]:
        try:
            fn()
        except Exception as e:
            print(f"{name} 發生錯誤：{e}")


if __name__ == "__main__":
    main()
