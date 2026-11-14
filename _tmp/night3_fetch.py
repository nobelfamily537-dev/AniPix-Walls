#!/usr/bin/env python3
"""Nightly gap-fill fetch: pull candidates for anime with zero wallpapers."""
import os, io, json, time, re, html
import requests, numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

SERIES = [
    ("horimiya", ["horimiya", "hori_kyouko", "miyamura_izumi"]),
    ("k-on", ["k-on!", "hirasawa_yui", "akiyama_mio", "nakano_azusa"]),
    ("your-lie-in-april", ["shigatsu_wa_kimi_no_uso", "miyazono_kaori", "arima_kousei"]),
    ("beastars", ["beastars", "legoshi", "haru_(beastars)"]),
    ("noragami", ["noragami", "yato_(noragami)", "ikiyo_hiyori"]),
    ("toradora", ["toradora!", "aisaka_taiga"]),
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
       "artist_request","text_focus","mosaic_censoring","bar_censor","photoshop","real_photo",
       "photo_(medium)","3d","cosplay"}

OUT = "_tmp/n3_prev"; SHEETS = "_tmp/n3_sheets"
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

def safebooru(tag):
    out = []
    for pid in (0, 1):
        r = get("https://safebooru.org/index.php",
                {"page": "dapi", "s": "post", "q": "index", "tags": tag + " sort:score:desc",
                 "limit": 100, "pid": pid}, sleep=1.2)
        if not r: break
        for m in re.finditer(r"<post\b([^>]*)/?>", r.text):
            a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
            try:
                w, h, sc = int(a.get("width", 0)), int(a.get("height", 0)), int(a.get("score", 0))
            except Exception:
                continue
            if sc < 30 or w < 900: continue
            prev = a.get("sample_url") or ""
            if "sample" not in prev:
                prev = f"https://safebooru.org/images/{a.get('directory')}/{a.get('image')}"
            out.append(dict(src="sb", id="sb" + a.get("id", ""), score=sc, w=w, h=h,
                            url=f"https://safebooru.org/images/{a.get('directory')}/{a.get('image')}",
                            prev=prev, tags=html.unescape(a.get("tags", ""))))
    return out

allc = []
for slug, tags in SERIES:
    pool = []
    for t in tags:
        pool += safebooru(t)
    seen, kept = set(), []
    pool.sort(key=lambda p: -(p["score"] or 0))
    for p in pool:
        if p["id"] in seen: continue
        seen.add(p["id"])
        w, h = p["w"], p["h"]
        r = h / w
        if not (0.6 <= r <= 2.3 and h >= 1100): continue
        if set(p["tags"].split()) & BAD: continue
        kept.append(p)
    # prefer portrait-ish sources first, then landscape
    kept.sort(key=lambda p: (0 if p["h"] / p["w"] >= 1.05 else 1, -(p["score"] or 0)))
    kept = kept[:14]
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

json.dump(allc, open("_tmp/n3_cands.json", "w"), indent=1)
print("TOTAL", len(allc), flush=True)
