#!/usr/bin/env python3
"""Low-count run 22 - wallhaven portrait fetch (stage 1b)."""
import os, io, json, time, re
import requests
from PIL import Image

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json,text/plain,*/*"}
OUT = "_tmp/lowrun22/preview"
os.makedirs(OUT, exist_ok=True)
picks = json.load(open("_tmp/lowrun22/picks.json"))
excl = set(json.load(open("_tmp/lowrun22/exclude.json")))
cands = json.load(open("_tmp/lowrun22/cands.json")) if os.path.exists("_tmp/lowrun22/cands.json") else []
have_pid = {(c["site"], c["pid"]) for c in cands}
API = "https://wallhaven.cc/api/v1/search"


def api(q, page):
    p = {"q": q, "categories": "010", "purity": "100", "ratios": "9x16,10x16,9x18",
         "atleast": "1080x1920", "sorting": "favorites", "order": "desc", "page": page}
    for _ in range(3):
        try:
            r = requests.get(API, params=p, headers=UA, timeout=30)
            if r.status_code == 200:
                time.sleep(1.0)
                return r.json()
            print("  HTTP", r.status_code, q, page, flush=True)
        except Exception as e:
            print("  ERR", type(e).__name__, q, flush=True)
        time.sleep(3)
    return {}


for pk in picks:
    name, slug = pk["series"], pk["slug"]
    pool = []
    for q in pk["booru"]:
        for page in (1, 2):
            js = api(q, page)
            for it in js.get("data", []):
                pool.append(it)
            if len(js.get("data", [])) < 24:
                break
    print("== %s pool=%d" % (name, len(pool)), flush=True)
    seen, kept = set(), []
    for it in pool:
        wid = it["id"]
        if wid in seen or wid in excl:
            continue
        seen.add(wid)
        w, h = it["dimension_x"], it["dimension_y"]
        if w < 1000 or h < 1700:
            continue
        r = w / h
        if not (0.48 <= r <= 0.62):
            continue
        kept.append(it)
    print("   valid=%d" % len(kept), flush=True)
    n = 0
    existing = len([f for f in os.listdir(OUT) if f.startswith(slug + "_")])
    for it in kept:
        if n >= 14:
            break
        key = ("https://wallhaven.cc/", it["id"])
        if key in have_pid:
            continue
        try:
            r = requests.get(it["path"], headers=UA, timeout=45)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            im = im.resize((420, 746), Image.LANCZOS)
            fn = "%s_w%02d.jpg" % (slug, n)
            im.save(os.path.join(OUT, fn), "JPEG", quality=84, optimize=True)
            cands.append(dict(series=name, file=fn, pid=it["id"], site="https://wallhaven.cc/",
                              score=it.get("favorites", 0), w=it["dimension_x"], h=it["dimension_y"],
                              url=it["path"], tags=" ".join(t["name"].replace(" ", "_") for t in it.get("tags", []))[:600],
                              source_page=it.get("url", "")))
            have_pid.add(key)
            n += 1
        except Exception as e:
            print("   dl err", it["id"], type(e).__name__, flush=True)
        time.sleep(0.15)
    print("   previews=%d" % n, flush=True)

json.dump(cands, open("_tmp/lowrun22/cands.json", "w"), indent=1)
print("TOTAL candidates", len(cands), flush=True)
