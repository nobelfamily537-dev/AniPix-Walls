#!/usr/bin/env python3
"""Fill src_tags for wallhaven candidates using the per-wallpaper API."""
import json, time, requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
p = "_tmp/lc/approved.json"
a = json.load(open(p))
cache = {}
for it in a["items"]:
    k = it["key"]
    if it.get("src_tags"):
        continue
    if not k.startswith("wh"):
        continue
    wid = k[2:]
    if wid in cache:
        it["src_tags"] = cache[wid]
        continue
    for attempt in range(3):
        try:
            r = requests.get(f"https://wallhaven.cc/api/v1/w/{wid}", headers=UA, timeout=30)
            if r.status_code == 200:
                d = r.json().get("data", {})
                names = [t.get("name", "") for t in (d.get("tags") or []) if t.get("name")]
                cache[wid] = names
                it["src_tags"] = names
                print(wid, len(names), ",".join(names[:8]))
                break
            print("HTTP", r.status_code, wid)
        except Exception as e:
            print("ERR", wid, e)
        time.sleep(2)
    time.sleep(0.6)
json.dump(a, open(p, "w"), indent=1)
print("done", sum(1 for i in a["items"] if i.get("src_tags")), "of", len(a["items"]))
