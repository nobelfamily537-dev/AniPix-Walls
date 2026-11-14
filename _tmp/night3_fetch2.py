#!/usr/bin/env python3
"""Nightly gap-fill fetch v4: safebooru (fixed parsing) portrait candidates."""
import os, io, json, time, re, html
import requests, numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

SERIES = [
    ("horimiya", ["hori-san_to_miyamura-kun", "hori_kyouko", "miyamura_izumi", "hori_(hori-san_to_miyamura-kun)"]),
    ("k-on", ["k-on!", "hirasawa_yui", "akiyama_mio", "nakano_azusa", "tainaka_ritsu", "kotobuki_tsumugi"]),
    ("toradora", ["toradora!", "aisaka_taiga", "takasu_ryuuji", "kushieda_minori"]),
    ("tower-of-god", ["tower_of_god", "kami_no_tou", "twenty-fifth_baam", "khun_aguero_agnes", "rachel_(tower_of_god)"]),
]

BAD = {"text","english_text","watermark","signature","artist_name","speech_bubble","comic","4koma",
       "multiple_views","character_sheet","translated","logo","border","frame","letterboxed",
       "twitter_username","web_address","dated","artist_logo","english_commentary","bad_id",
       "bad_pixiv_id","bad_twitter_id","official_art","sketch","monochrome","greyscale",
       "partially_colored","gun","vehicle","blood","gore","censored","manga","scan","sample",
       "no_humans","food","chibi","comic_panel","bikini","swimsuit","underwear","lingerie","panties",
       "bra","cleavage","no_bra","see_through","cameltoe","spread_legs","large_breasts","huge_breasts",
       "ass","nude","naked","topless","wet","bed","bottomless","sideboob","underboob","loli",
       "cropped","faceless","pantyshot","upskirt","skirt_lift","translation_request","commentary",
       "artist_request","text_focus","mosaic_censoring","bar_censor","cosplay","photo","real_photo",
       "3d","sketch_page","lineart","flat_color","lowres","jpeg_artifacts","bad_anatomy","extra_arms",
       "extra_legs","missing_limbs","weapon_focus","head_out_of_frame","knee_boots","thighhighs_only"}

OUT = "_tmp/n3b_prev"; SHEETS = "_tmp/n3b_sheets"
os.makedirs(OUT, exist_ok=True); os.makedirs(SHEETS, exist_ok=True)
TARGET = 9 / 16

def get(url, params=None, tries=3, sleep=1.0):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=90)
            if r.status_code == 200:
                time.sleep(sleep); return r
            print("  HTTP", r.status_code, url, flush=True)
        except Exception as e:
            print("  ERR", e, flush=True)
        time.sleep(4)
    return None

def smart_crop(im):
    w, h = im.size
    r = h / w
    if r > TARGET * 1.02:
        nh = int(w / TARGET); y = int((h - nh) * 0.05)
        return im.crop((0, y, w, y + nh))
    if r >= TARGET:
        return im
    nw = int(h * TARGET)
    gw = 200
    g = im.convert("L").resize((gw, max(20, int(gw * h / w))), Image.LANCZOS)
    a = np.asarray(g.filter(ImageFilter.FIND_EDGES), dtype=np.float32)
    col = np.convolve(a.mean(axis=0), np.ones(7) / 7, "same")
    win = max(2, int(round(nw * gw / w)))
    xs = np.arange(len(col) - win + 1)
    if len(xs) <= 0:
        x = (w - nw) // 2
    else:
        centre = (len(col) - win) / 2
        bias = np.exp(-((xs - centre) ** 2) / (2 * (len(col) * 0.30) ** 2))
        scores = np.array([col[x:x + win].sum() for x in xs]) * bias
        x = int(xs[int(np.argmax(scores))] * w / gw)
    x = max(0, min(w - nw, x))
    return im.crop((x, 0, x + nw, h))

def num(v, d=0):
    try:
        return int(float(v))
    except Exception:
        return d

def safebooru(tag):
    out = []
    for pid in (0, 1, 2):
        r = get("https://safebooru.org/index.php",
                {"page": "dapi", "s": "post", "q": "index", "tags": tag,
                 "limit": 100, "pid": pid}, sleep=1.2)
        if not r: break
        found = 0
        for m in re.finditer(r"<post\b([^>]*)/?>", r.text):
            a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
            found += 1
            w, h = num(a.get("width")), num(a.get("height"))
            if w < 800 or h < 1000: continue
            if a.get("rating", "s") in ("e", "q"): continue
            prev = a.get("sample_url") or a.get("file_url") or ""
            out.append(dict(src="sb", id="sb" + a.get("id", ""), score=w * h, w=w, h=h,
                            url=a.get("file_url", ""), prev=prev,
                            tags=html.unescape(a.get("tags", "")).strip()))
        print(f"   sb[{tag}] pid{pid} posts={found} kept={len(out)}", flush=True)
        if found < 100: break
    return out

allc = []
for slug, tags in SERIES:
    pool = []
    for t in tags:
        pool += safebooru(t)
    seen, kept = set(), []
    for p in sorted(pool, key=lambda p: -p["score"]):
        if p["id"] in seen: continue
        seen.add(p["id"])
        r = p["h"] / p["w"]
        if not (0.58 <= r <= 2.2): continue
        if set(p["tags"].split()) & BAD: continue
        kept.append(p)
    kept.sort(key=lambda p: (0 if p["h"] / p["w"] >= 1.05 else 1, -p["score"]))
    kept = kept[:16]
    print(f"== {slug}: pool={len(pool)} kept={len(kept)}", flush=True)
    mine = []
    for i, p in enumerate(kept):
        fn = f"{slug}_{i:02d}.jpg"
        try:
            r = requests.get(p["prev"], headers=UA, timeout=90); r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            if im.width < 400: raise ValueError("tiny")
            ImageOps.fit(smart_crop(im), (500, 889), method=Image.LANCZOS).save(
                os.path.join(OUT, fn), "JPEG", quality=85, optimize=True)
            rec = dict(slug=slug, file=fn, **p); allc.append(rec); mine.append(rec)
        except Exception as e:
            print("  err", fn, e, flush=True)
        time.sleep(0.2)
    if mine:
        cw, ch, cols = 300, 533, 4
        rows = (len(mine) + cols - 1) // cols
        sheet = Image.new("RGB", (cw * cols, ch * rows), (20, 20, 20))
        d = ImageDraw.Draw(sheet)
        for i, rec in enumerate(mine):
            im = Image.open(os.path.join(OUT, rec["file"])).resize((cw, ch), Image.LANCZOS)
            x, y = (i % cols) * cw, (i // cols) * ch
            sheet.paste(im, (x, y))
            d.rectangle([x, y, x + 40, y + 24], fill=(0, 0, 0))
            d.text((x + 6, y + 6), f"{i}", fill=(255, 255, 0))
        sheet.save(os.path.join(SHEETS, f"{slug}.jpg"), "JPEG", quality=82, optimize=True)

json.dump(allc, open("_tmp/n3b_cands.json", "w"), indent=1)
print("TOTAL", len(allc), flush=True)
