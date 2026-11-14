#!/usr/bin/env python3
"""Nightly gap-fill fetch v2: wallhaven-first candidates for anime with zero wallpapers."""
import os, io, json, time, re, html
import requests, numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

SERIES = [
    ("horimiya", ["horimiya", "hori kyouko", "miyamura izumi"]),
    ("k-on", ["k-on!", "k-on", "yui hirasawa", "mio akiyama"]),
    ("your-lie-in-april", ["your lie in april", "shigatsu wa kimi no uso", "kaori miyazono"]),
    ("beastars", ["beastars", "legoshi", "haru beastars"]),
    ("noragami", ["noragami", "yato", "hiyori ikiyo"]),
    ("toradora", ["toradora", "toradora!", "taiga aisaka"]),
    ("erased", ["erased", "boku dake ga inai machi", "satoru fujinuma"]),
    ("tower-of-god", ["tower of god", "kami no tou", "twenty fifth baam"]),
]

BAD = {"text","english_text","watermark","signature","artist_name","speech_bubble","comic","4koma",
       "multiple_views","character_sheet","translated","logo","border","frame","letterboxed",
       "twitter_username","web_address","dated","artist_logo","english_commentary","bad_id",
       "monochrome","greyscale","partially_colored","gun","vehicle","blood","gore","censored",
       "manga","scan","sample","no_humans","food","chibi","comic_panel","bikini","swimsuit",
       "underwear","lingerie","panties","bra","cleavage","no_bra","see_through","spread_legs",
       "large_breasts","huge_breasts","ass","nude","naked","topless","wet","bed","bottomless",
       "sideboob","underboob","loli","cropped","faceless","pantyshot","upskirt","skirt_lift",
       "cosplay","photo","3d","real","person","people"}

OUT = "_tmp/n3_prev"; SHEETS = "_tmp/n3_sheets"
os.makedirs(OUT, exist_ok=True); os.makedirs(SHEETS, exist_ok=True)
TARGET = 9 / 16

# wallhaven ids already used by the app
used = set()
try:
    wp = json.load(open("wallpapers.json"))
    for c in wp["categories"].values():
        for e in c:
            for f in (e.get("full"), e.get("thumb")):
                m = re.search(r"wallhaven-([a-z0-9]+)\.(?:jpg|png|jpeg|webp)", f or "")
                if m: used.add(m.group(1))
                m2 = re.search(r"/wh-([a-z0-9]+)\.(?:jpg|png|jpeg|webp)", f or "")
                if m2: used.add(m2.group(1))
except Exception as e:
    print("wp read err", e, flush=True)
print("used wallhaven ids", len(used), flush=True)

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

def wallhaven(q, ratios):
    out = []
    for page in (1, 2, 3):
        r = get("https://wallhaven.cc/api/v1/search",
                {"q": q, "categories": "010", "purity": "100", "ratios": ratios,
                 "sorting": "favorites", "page": page}, sleep=1.2)
        if not r: break
        try:
            js = r.json()
        except Exception:
            break
        for d in js.get("data", []):
            out.append(dict(src="wh", id=d["id"], score=(d.get("favorites") or 0),
                            w=d["dimension_x"], h=d["dimension_y"], url=d["path"],
                            prev=(d.get("thumbs") or {}).get("large") or d["path"],
                            tags=" ".join(t["name"] for t in d.get("tags", []))))
        meta = js.get("meta", {})
        if meta.get("current_page", 1) >= meta.get("last_page", 1): break
    return out

def safebooru(tag):
    out = []
    r = get("https://safebooru.org/index.php",
            {"page": "dapi", "s": "post", "q": "index", "tags": tag + " sort:score:desc",
             "limit": 100, "pid": 0}, sleep=1.0)
    if not r: return out
    n = 0
    for m in re.finditer(r"<post\b([^>]*)/?>", r.text):
        n += 1
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
    print(f"   sb[{tag}] posts={n} kept={len(out)}", flush=True)
    return out

# quick sanity check on the booru API
safebooru("hatsune_miku")

allc = []
for slug, queries in SERIES:
    pool = []
    for q in queries:
        a = wallhaven(q, "portrait")
        b = wallhaven(q, "landscape")
        print(f"   wh[{q}] port={len(a)} land={len(b)}", flush=True)
        pool += a + b
        pool += safebooru(q.replace(" ", "_"))
    seen, kept = set(), []
    pool.sort(key=lambda p: -(p["score"] or 0))
    for p in pool:
        if p["id"] in seen: continue
        seen.add(p["id"])
        if p["src"] == "wh" and p["id"] in used: continue
        w, h = p["w"], p["h"]
        r = h / w
        if not (0.62 <= r <= 2.3 and h >= 1200 and w >= 900): continue
        if set(p["tags"].split()) & BAD: continue
        kept.append(p)
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
