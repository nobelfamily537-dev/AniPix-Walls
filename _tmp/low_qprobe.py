#!/usr/bin/env python3
"""Probe wallhaven query semantics."""
import json, time
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
QUERIES = ['soul eater', '"soul eater"', 'tag:soul_eater', 'soul+eater', '"princess mononoke"',
           '"kaiju no. 8"', '"dungeon meshi"', '"initial d"', '"black clover"', '"cyberpunk edgerunners"']

for q in QUERIES:
    try:
        r = requests.get("https://wallhaven.cc/api/v1/search",
                         {"q": q, "categories": "010", "purity": "100", "atleast": "1080x1500",
                          "sorting": "favorites"}, headers=UA, timeout=20)
        if r.status_code != 200:
            print(json.dumps({"q": q, "http": r.status_code}), flush=True)
            time.sleep(1.5)
            continue
        js = r.json()
        data = js.get("data", [])
        samples = []
        for d in data[:5]:
            tags = [t["name"] for t in d.get("tags", [])][:6]
            samples.append({"id": d["id"], "tags": tags})
        print(json.dumps({"q": q, "total": js.get("meta", {}).get("total"), "n": len(data), "samples": samples}), flush=True)
    except Exception as e:
        print(json.dumps({"q": q, "err": type(e).__name__}), flush=True)
    time.sleep(1.5)
print("DONE", flush=True)
