#!/usr/bin/env python3
"""Debug: why safebooru candidates all rejected."""
import json, re
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
      "Referer": "https://safebooru.org/"}
API = "https://safebooru.org/index.php"

r = requests.get(API, params={"page": "dapi", "s": "post", "q": "index", "json": 1,
                              "tags": "sakurajima_mai rating:safe", "limit": 100, "pid": 0},
                 headers=UA, timeout=30)
print("HTTP", r.status_code, "len", len(r.content), flush=True)
js = r.json()
print("n", len(js), flush=True)
print("keys0", list(js[0].keys()), flush=True)
print("ratings", sorted({p.get("rating") for p in js}), flush=True)
print("ids", [p.get("id") for p in js[:5]], flush=True)
print("urls", [p.get("file_url") for p in js[:3]], flush=True)
dims = [(p.get("width"), p.get("height")) for p in js[:15]]
print("dims", dims, flush=True)
print("tags0", js[0].get("tags"), flush=True)
print("tags1", js[1].get("tags"), flush=True)
# ratios
port = [p for p in js if (p.get("height") or 0) / max(p.get("width") or 1, 1) >= 1.22]
print("portrait count", len(port), flush=True)
big = [p for p in port if (p.get("width") or 0) >= 850 and (p.get("height") or 0) >= 1250]
print("portrait+big", len(big), flush=True)
