#!/usr/bin/env python3
"""Temporary nightly gap-fetch: pull portrait anime art from Wallhaven for
series that have no coverage yet, normalise to 1080x1920 + 360x640 thumbs,
and write everything into staging/ (committed to a throwaway branch)."""
import os, json, io, time, hashlib, requests
from PIL import Image, ImageOps

QUERIES = [
    "ousama ranking", "bojji", "skip to loafer", "iwakura mitsumi",
    "boku no kokoro no yabai yatsu", "yamada anna", "josee to tora to sakana tachi",
    "summer time rendering", "golden kamuy", "asirpa", "dororo", "hyakkimaru",
    "megalo box", "vivy", "perfect blue", "nichijou", "zombie land saga",
    "love live", "k-on", "maquia", "wolf children", "ranking of kings",
]
PER = 5
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
os.makedirs("staging", exist_ok=True)
manifest = []

for q in QUERIES:
    for ratio_set in ("9x16,10x16,2x3", ""):
        params = {"q": q, "categories": "010", "purity": "100",
                  "sorting": "toplist", "order": "desc", "topRange": "1M",
                  "atleast": "900x1400", "page": "1"}
        if ratio_set:
            params["ratios"] = ratio_set
        try:
            r = requests.get("https://wallhaven.cc/api/v1/search", params=params,
                             headers=UA, timeout=60)
            r.raise_for_status()
            items = r.json().get("data", [])
        except Exception as e:
            print("APIERR", q, e); items = []
        if len(items) >= PER:
            break
        if not ratio_set:
            break
        time.sleep(1)

    got = 0
    for it in items:
        if got >= PER:
            break
        try:
            resp = requests.get(it["path"], headers=UA, timeout=90)
            resp.raise_for_status()
            im = Image.open(io.BytesIO(resp.content)).convert("RGB")
            if im.width < 800 or im.height < 1200:
                continue
            wid = "s" + hashlib.md5(it["id"].encode()).hexdigest()[:9]
            full = ImageOps.fit(im, (1080, 1920), method=Image.LANCZOS,
                                centering=(0.5, 0.36))
            full.save(f"staging/{wid}.jpg", "JPEG", quality=95, optimize=True,
                      progressive=True)
            full.resize((360, 640), Image.LANCZOS).save(
                f"staging/{wid}_thumb.jpg", "JPEG", quality=80, optimize=True,
                progressive=True)
            manifest.append({"file": wid, "query": q, "wh": it["id"],
                             "res": f'{it.get("dimension_x")}x{it.get("dimension_y")}',
                             "tags": [t["name"] for t in it.get("tags", [])],
                             "src": it["path"], "page": it.get("url", "")})
            got += 1
        except Exception as e:
            print("IMGERR", it.get("id"), e)
        time.sleep(0.2)
    print(f"QUERY {q!r}: hits={len(items)} kept={got}")

json.dump(manifest, open("staging/manifest.json", "w"), indent=1)
print("TOTAL", len(manifest))
