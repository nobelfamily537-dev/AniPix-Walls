#!/usr/bin/env python3
"""Nightly gap-fill: wallhaven candidates for anime with ZERO coverage in the app."""
import os, io, json, time, re
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

SERIES = [
    ("steins-gate", ["steins gate", "steins;gate", "kurisu makise", "okabe rintarou", "mayuri shiina", "steins gate kurisu", "makise kurisu"]),
    ("code-geass", ["code geass", "lelouch", "lelouch vi britannia", "c.c. code geass", "kallen kouzuki", "code geass lelouch", "geass"]),
    ("cowboy-bebop", ["cowboy bebop", "spike spiegel", "faye valentine", "edward wong", "bebop anime", "cowboy bebop spike"]),
    ("monogatari", ["monogatari", "bakemonogatari", "senjougahara", "shinobu oshino", "hachikuji", "monogatari series", "oshino shinobu"]),
    ("vinland-saga", ["vinland saga", "thorfinn", "askeladd", "canute vinland saga", "vinland saga thorfinn", "thorfinn vinland"]),
    ("mob-psycho", ["mob psycho 100", "mob psycho", "shigeo kageyama", "reigen arataka", "mob psycho 100 reigen"]),
    ("kill-la-kill", ["kill la kill", "ryuko matoi", "matoi ryuuko", "kill la kill ryuko", "satsuki kiryuin"]),
    ("overlord", ["overlord anime", "ainz ooal gown", "albedo overlord", "overlord ainz", "shalltear bloodfallen"]),
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
SHEETS = "_tmp/night_sheets"
os.makedirs(OUT, exist_ok=True); os.makedirs(SHEETS, exist_ok=True)

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
print("used ids:", len(used), flush=True)

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
        for page in (1, 2, 3):
            r = get("https://wallhaven.cc/api/v1/search",
                    {"q": q, "categories": "010", "purity": "100", "ratios": "portrait",
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
        if p["h"] / p["w"] < 1.45 or p["h"] < 1800: continue
        if set(p["tags"].split()) & BAD: continue
        kept.append(p)
    kept = kept[:12]
    print(f"== {slug}: pool={len(pool)} kept={len(kept)}", flush=True)
    mine = []
    for i, p in enumerate(kept):
        fn = f"{slug}_{i:02d}.jpg"
        try:
            r = requests.get(p["prev"], headers=UA, timeout=90); r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            render(im).save(os.path.join(OUT, fn), "JPEG", quality=82, optimize=True)
            rec = dict(slug=slug, file=fn, **p); allc.append(rec); mine.append(rec)
        except Exception as e:
            print("  err", fn, e, flush=True)
        time.sleep(0.2)
    # contact sheet 4 x 3 of 240x427 cells
    if mine:
        cw, ch, cols = 240, 427, 4
        rows = (len(mine) + cols - 1) // cols
        sheet = Image.new("RGB", (cw*cols, ch*rows), (20, 20, 20))
        d = ImageDraw.Draw(sheet)
        for i, rec in enumerate(mine):
            im = Image.open(os.path.join(OUT, rec["file"])).resize((cw, ch), Image.LANCZOS)
            x, y = (i % cols)*cw, (i//cols)*ch
            sheet.paste(im, (x, y))
            d.rectangle([x, y, x+44, y+26], fill=(0, 0, 0))
            d.text((x+6, y+6), f"{i}", fill=(255, 255, 0))
        sheet.save(os.path.join(SHEETS, f"{slug}.jpg"), "JPEG", quality=80, optimize=True)

json.dump(allc, open("_tmp/night_cands.json", "w"), indent=1)
print("TOTAL", len(allc), flush=True)
