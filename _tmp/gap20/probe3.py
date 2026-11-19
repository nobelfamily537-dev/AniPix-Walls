#!/usr/bin/env python3
"""Probe wallhaven portrait coverage for gap series."""
import json
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
      "Accept": "application/json"}

QUERIES = [
    ("yoko littner", {}),
    ("yoko littner", {"ratios": "9x16"}),
    ("gurren lagann", {"ratios": "9x16"}),
    ("jojo", {"ratios": "9x16"}),
    ("jojo bizarre", {"ratios": "9x16"}),
    ("jotaro", {"ratios": "9x16"}),
    ("dio brando", {"ratios": "9x16"}),
    ("fruits basket", {"ratios": "9x16"}),
    ("tohru honda", {"ratios": "9x16"}),
    ("mai sakurajima", {"ratios": "9x16"}),
    ("bunny girl senpai", {"ratios": "9x16"}),
    ("yukino yukinoshita", {"ratios": "9x16"}),
    ("oregairu", {"ratios": "9x16"}),
    ("", {"ratios": "9x16", "sorting": "toplist", "topRange": "1M"}),
]

for q, extra in QUERIES:
    p = {"q": q, "categories": "010", "purity": "100", "atleast": "1000x1700"}
    p.update(extra)
    try:
        r = requests.get("https://wallhaven.cc/api/v1/search", params=p, headers=UA, timeout=25)
        js = r.json()
        meta = js.get("meta", {})
        data = js.get("data", [])
        print("q=%-20s %-28s total=%s got=%d" % (q, extra, meta.get("total"), len(data)), flush=True)
        for d in data[:3]:
            print("    %s %sx%s %s" % (d["id"], d["dimension_x"], d["dimension_y"], d["path"][:80]), flush=True)
    except Exception as e:
        print("q=%-20s ERR %s" % (q, type(e).__name__), flush=True)
