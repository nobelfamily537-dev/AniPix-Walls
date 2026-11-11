#!/usr/bin/env python3
"""Phase 5: wallhaven-sourced candidates for the two game series."""
import os, io, json, time, re
import requests
from PIL import Image

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
SERIES = [
    ("blue archive", ["blue archive", "shiroko", "arona", "hina blue archive", "mika blue archive", "yuuka blue archive", "aru blue archive", "blue archive game"]),
    ("arknights", ["arknights", "amiya", "surtr", "skadi", "texas arknights", "chen arknights", "arknights game"]),
]
BAD = {"text","english_text","watermark","signature","speech_bubble","comic","4koma","multiple_views",
       "character_sheet","logo","border","frame","letterboxed","bikini","swimsuit","underwear","lingerie",
       "panties","bra","cleavage","no_bra","see_through","cameltoe","spread_legs","large breasts","huge breasts",
       "ass","nude","naked","topless","bed","thighs","gun","mecha","vehicle"}
OUT = "_tmp/prev5"
os.makedirs(OUT, exist_ok=True)
cands = []

def get(url, params=None, sleep=1.1):
    for i in range(2):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=60)
            if r.status_code == 200:
                time.sleep(sleep); return r
            print("  HTTP", r.status_code, flush=True)
        except Exception as e:
            print("  ERR", e, flush=True)
        time.sleep(3)
    return None

def render(im, size=(450, 800)):
    w, h = im.size; r = h / w; tw, th = size; t = 9/16
    if r > t:
        nh = int(w/t); y = int((h-nh)*(0.05 if r >= 1.55 else 0.18))
        return im.crop((0, y, w, y+nh))
    nw = int(h*t); x = (w-nw)//2
    return im.crop((x, 0, x+nw, h))

for name, queries in SERIES:
    pool = []
    for q in queries:
        for page in (1, 2, 3):
            r = get("https://wallhaven.cc/api/v1/search",
                    {"q": q, "categories": "010", "purity": "100", "ratios": "9x16",
                     "atleast": "1080x1920", "sorting": "favorites", "page": page})
            if not r: break
            try: js = r.json()
            except Exception: break
            for d in js.get("data", []):
                pool.append(dict(src="wallhaven", id=d["id"], score=(d.get("favorites") or 0),
                                 w=d["dimension_x"], h=d["dimension_y"], url=d["path"],
                                 prev=(d.get("thumbs") or {}).get("large") or d["path"],
                                 md5=d["id"], tags=" ".join(t["name"] for t in d.get("tags", []))))
            if js.get("meta", {}).get("current_page", 1) >= js.get("meta", {}).get("last_page", 1): break
    print(f"== {name}: pool={len(pool)}", flush=True)
    seen, kept = set(), []
    pool.sort(key=lambda p: -(p["score"] or 0))
    for p in pool:
        if p["md5"] in seen: continue
        seen.add(p["md5"])
        if p["h"] / p["w"] < 1.5 or p["h"] < 1800: continue
        if set(p["tags"].split()) & BAD: continue
        kept.append(p)
    kept = kept[:30]
    print(f"   kept {len(kept)}", flush=True)
    slug = re.sub(r"[^a-z0-9]+", "-", name)
    for i, p in enumerate(kept):
        try:
            r = requests.get(p["prev"], headers=UA, timeout=90)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            render(im).save(f"{OUT}/{slug}_{i:02d}.jpg", "JPEG", quality=82, optimize=True)
            cands.append(dict(series=name, file=f"{slug}_{i:02d}.jpg", src=p["src"], pid=p["id"],
                              score=p["score"], w=p["w"], h=p["h"], url=p["url"], tags=p["tags"]))
        except Exception as e:
            print("   dl err", p.get("id"), e, flush=True)
        time.sleep(0.2)
json.dump(cands, open("_tmp/candidates5.json", "w"), indent=1)
print("TOTAL candidates", len(cands), flush=True)
