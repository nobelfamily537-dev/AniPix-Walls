#!/usr/bin/env python3
"""Temporary nightly gap-fetch: pull portrait anime art from Wallhaven for
series with no coverage yet, normalise to 1080x1920 + 360x640 thumbs, and
write everything into staging/ (committed to a throwaway branch)."""
import os, json, io, time, hashlib, requests
from PIL import Image, ImageOps

QUERIES = [
    "ousama ranking", "bojji", "skip to loafer", "iwakura mitsumi",
    "boku no kokoro no yabai yatsu", "yamada anna", "josee to tora to sakana tachi",
    "summer time rendering", "kofune ushio", "golden kamuy", "asirpa",
    "dororo", "hyakkimaru", "megalo box", "vivy", "perfect blue",
    "nichijou", "zombie land saga", "love live", "k-on", "maquia",
    "wolf children", "the girl who leapt through time", "summer wars",
    "whisper of the heart", "arrietty", "the boy and the heron",
    "in this corner of the world", "ride your wave", "hello world",
    "promare", "yuri on ice", "banana fish", "blue period", "slam dunk",
    "kuroko no basket", "princess principal", "girls und panzer",
    "azur lane", "umamusume", "bang dream", "idolmaster", "paprika",
    "redline", "vampire hunter d", "ghost in the shell", "kingdom anime",
    "odd taxi", "86 eighty six", "bakuman", "honey and clover",
]
PER = 6
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
os.makedirs("staging", exist_ok=True)
manifest = []

def search(q, atleast):
    params = {"q": q, "categories": "010", "purity": "100",
              "sorting": "relevance", "order": "desc", "page": "1"}
    if atleast:
        params["atleast"] = atleast
    r = requests.get("https://wallhaven.cc/api/v1/search", params=params,
                     headers=UA, timeout=60)
    r.raise_for_status()
    return r.json().get("data", [])

for q in QUERIES:
    items = []
    for atleast in ("1200x1800", "800x1200", ""):
        try:
            items = search(q, atleast)
        except Exception as e:
            print("APIERR", q, e); items = []
        print(f"  try {q!r} atleast={atleast!r} hits={len(items)}")
        if len(items) >= 3:
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
            if im.width < 700 or im.height < 1000:
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
    print(f"QUERY {q!r}: kept={got}")

json.dump(manifest, open("staging/manifest.json", "w"), indent=1)
print("TOTAL", len(manifest))
