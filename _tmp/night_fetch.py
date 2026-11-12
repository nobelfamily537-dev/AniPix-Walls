#!/usr/bin/env python3
"""Nightly gap-fill: wallhaven candidates for anime with ZERO coverage in the app."""
import os, io, json, time, re
import requests
from PIL import Image, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

SERIES = [
    ("steins-gate", ["steins gate", "steins;gate", "kurisu makise", "okabe rintarou", "mayuri shiina", "steins gate kurisu"]),
    ("code-geass", ["code geass", "lelouch", "lelouch vi britannia", "c.c. code geass", "kallen kouzuki", "code geass lelouch"]),
    ("cowboy-bebop", ["cowboy bebop", "spike spiegel", "faye valentine", "edward wong", "bebop anime"]),
    ("monogatari", ["monogatari", "bakemonogatari", "senjougahara", "shinobu oshino", "hachikuji", "monogatari series"]),
    ("vinland-saga", ["vinland saga", "thorfinn", "askeladd", "canute vinland saga", "vinland saga thorfinn"]),
]

BAD = {"text","english_text","watermark","signature","artist_name","speech_bubble","comic","4koma",
       "multiple_views","character_sheet","translated","logo","border","frame","letterboxed",
       "twitter_username","web_address","dated","artist_logo","english_commentary","bad_id",
       "bad_pixiv_id","bad_twitter_id","official_art","sketch","monochrome","greyscale",
       "partially_colored","gun","mecha","vehicle","blood","gore","censored","manga","scan","sample",
       "no_humans","food","chibi","comic_panel","bikini","swimsuit","underwear","lingerie","panties",
       "bra","cleavage","no_bra","see_through","cameltoe","spread_legs","large_breasts","huge_breasts",
       "ass","nude","naked","topless","wet","bed","bottomless","sideboob","underboob","loli"}
OUT = "_tmp/night_prev"
os.makedirs(OUT, exist_ok=True)

# wallhaven ids already used in the app
used = set()
try:
    wp = json.load(open("wallpapers.json"))
    for cat, ents in wp["categories"].items():
        for e in ents:
            for f in (e.get("full"), e.get("thumb")):
                m = re.search(r"wallhaven-([a-z0-9]+)\.(?:jpg|png|jpeg|webp)", f or "")
                if m: used.add(m.group(1))
except Exception as ex:
    print("used-id scan failed", ex, flush=True)

def get(url, params=None, tries=3, sleep=1.1):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=60)
            if r.status_code == 200:
                time.sleep(sleep); return r
            print("  HTTP", r.status_code, url, flush=True)
        except Exception as e:
            print("  ERR", e, flush=True)
        time.sleep(4)
    return None

def render(im, size=(450, 800)):
    w, h = im.size; r = h / w; tw, th = size; t = 9/16
    if r > 2.05:
        bg = ImageOps.fit(im, (tw, th), method=Image.LANCZOS).filter(ImageFilter.GaussianBlur(22))
        fg = im.copy(); fg.thumbnail((tw, th), Image.LANCZOS)
        bg.paste(fg, ((tw-fg.width)//2, (th-fg.height)//2)); return bg
    if r > t:
        nh = int(w/t); y = int((h-nh)*(0.04 if r >= 1.55 else 0.18)); return im.crop((0, y, w, y+nh))
    nw = int(h*t); x = (w-nw)//2; return im.crop((x, 0, x+nw, h))

allc = []
for slug, queries in SERIES:
    pool = []
    for q in queries:
        for page in (1, 2):
            r = get("https://wallhaven.cc/api/v1/search",
                    {"q": q, "categories": "010", "purity": "100", "ratios": "9x16",
                     "atleast": "1080x1920", "sorting": "favorites", "page": page})
            if not r: break
            try: js = r.json()
            except Exception: break
            for d in js.get("data", []):
                pool.append(dict(id=d["id"], score=(d.get("favorites") or 0),
                                 w=d["dimension_x"], h=d["dimension_y"], url=d["path"],
                                 prev=(d.get("thumbs") or {}).get("large") or d["path"],
                                 tags=" ".join(t["name"] for t in d.get("tags", []))))
            if js.get("meta", {}).get("current_page", 1) >= js.get("meta", {}).get("last_page", 1): break
    seen, kept = set(), []
    pool.sort(key=lambda p: -(p["score"] or 0))
    for p in pool:
        if p["id"] in seen or p["id"] in used: continue
        seen.add(p["id"])
        if p["h"] / p["w"] < 1.5 or p["h"] < 1800: continue
        if set(p["tags"].split()) & BAD: continue
        kept.append(p)
    kept = kept[:28]
    print(f"== {slug}: pool={len(pool)} kept={len(kept)}", flush=True)
    for i, p in enumerate(kept):
        fn = f"{slug}_{i:02d}.jpg"
        try:
            r = requests.get(p["prev"], headers=UA, timeout=90); r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            render(im).save(os.path.join(OUT, fn), "JPEG", quality=82, optimize=True)
            allc.append(dict(slug=slug, file=fn, **p))
        except Exception as e:
            print("  err", fn, e, flush=True)
        time.sleep(0.2)
json.dump(allc, open("_tmp/night_cands.json", "w"), indent=1)
print("TOTAL", len(allc), flush=True)
