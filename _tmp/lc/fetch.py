#!/usr/bin/env python3
"""Low-count run: fetch candidates for series with the fewest wallpapers.

Sources: wallhaven.cc API (primary), safebooru.org API (fallback).
Outputs staged 1080x1920 JPEGs + thumbs + contact sheets + manifest.
"""
import os, io, json, re, time, hashlib
import requests
from PIL import Image, ImageDraw, ImageFont

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
ROOT = "_tmp/lc"
STAGE = f"{ROOT}/stage"
SHEETS = f"{ROOT}/sheets"
for d in (STAGE, SHEETS):
    os.makedirs(d, exist_ok=True)

TARGET = 9 / 16
MIN_W, MIN_H = 900, 1600          # after 9:16 crop, before resize
MAX_PER_SERIES = 24

# slug, exact series tag in wallpapers.json, category, wallhaven query, safebooru tags
PLAN = [
    ("elden-ring",              "elden ring",               "game",  "elden ring",              "elden_ring"),
    ("dark-souls",              "dark souls",               "game",  "dark souls",              "dark_souls"),
    ("suzume",                  "suzume",                   "anime", "suzume",                  "suzume_no_tojimari"),
    ("nikke",                   "Nikke",                    "game",  "nikke",                   "goddess_of_victory:_nikke"),
    ("honkai-impact",           "honkai impact",            "game",  "honkai impact",           "honkai_impact"),
    ("persona-3",               "persona 3",                "game",  "persona 3",               "persona_3"),
    ("serial-experiments-lain", "serial experiments lain",  "anime", "serial experiments lain", "serial_experiments_lain"),
    ("yugioh",                  "yugioh",                   "anime", "yu-gi-oh",                "yu-gi-oh!"),
    ("sakamoto-days",           "sakamoto days",            "anime", "sakamoto days",           "sakamoto_days"),
    ("classroom-of-the-elite",  "classroom of the elite",   "anime", "classroom of the elite",  "youkoso_jitsuryoku_shijou_shugi_no_kyoushitsu_e"),
    ("soul-eater",              "soul eater",               "anime", "soul eater",              "soul_eater"),
    ("honkai-star-rail",        "Honkai Star Rail",         "game",  "honkai star rail",        "honkai:_star_rail"),
]

BAD = {"text", "english_text", "watermark", "signature", "artist_name", "speech_bubble", "comic",
       "4koma", "multiple_views", "character_sheet", "translated", "logo", "border", "frame",
       "letterboxed", "twitter_username", "web_address", "dated", "artist_logo", "english_commentary",
       "bad_id", "bad_pixiv_id", "bad_twitter_id", "official_art", "sketch", "monochrome", "greyscale",
       "partially_colored", "gun", "vehicle", "blood", "gore", "censored", "manga", "scan", "sample",
       "food", "chibi", "comic_panel", "bikini", "swimsuit", "underwear", "lingerie", "panties",
       "bra", "cleavage", "no_bra", "see_through", "cameltoe", "spread_legs", "large_breasts",
       "huge_breasts", "ass", "nude", "naked", "topless", "wet", "bed", "bottomless", "sideboob",
       "underboob", "loli", "pantyshot", "upskirt", "skirt_lift", "mosaic_censoring", "bar_censor"}

wp = json.load(open("wallpapers.json"))
used_urls = set()
used_wh = set()
for cat, ents in wp["categories"].items():
    for e in ents:
        for f in (e.get("full"), e.get("thumb"), e.get("alt")):
            if not f:
                continue
            used_urls.add(f)
            m = re.search(r"wallhaven-([a-z0-9]+)\.(?:jpg|png|jpeg|webp)", f)
            if m:
                used_wh.add(m.group(1))
print("existing wallhaven ids:", len(used_wh), flush=True)


def get(url, params=None, tries=3, timeout=90, stream=False):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout, stream=stream)
            if r.status_code == 200:
                return r
            print("   HTTP", r.status_code, url, flush=True)
        except Exception as e:
            print("   ERR", type(e).__name__, e, flush=True)
        time.sleep(2 + 2 * i)
    return None


def smart_crop(im):
    w, h = im.size
    r = h / w
    if abs(r - TARGET) < 0.02:
        return im
    if r > TARGET:                      # too tall -> trim height, keep the upper band
        nh = int(round(w / TARGET))
        y = int((h - nh) * 0.08)
        return im.crop((0, y, w, y + nh))
    nw = int(round(h * TARGET))         # too wide -> centre crop
    x = (w - nw) // 2
    return im.crop((x, 0, x + nw, h))


def process(raw, key, outdir):
    try:
        im = Image.open(io.BytesIO(raw))
        im.load()
    except Exception as e:
        print("   bad image", key, e, flush=True)
        return None
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (12, 12, 16))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")
    if im.width < 700 or im.height < 900:
        return None
    im = smart_crop(im)
    if im.width < MIN_W or im.height < MIN_H:
        return None
    if im.width > 1400:                 # avoid storing huge originals
        pass
    full = im.resize((1080, 1920), Image.LANCZOS)
    thumb = full.resize((360, 640), Image.LANCZOS)
    fp = os.path.join(outdir, f"{key}.jpg")
    tp = os.path.join(outdir, f"{key}_thumb.jpg")
    full.save(fp, "JPEG", quality=95, optimize=True, progressive=True)
    thumb.save(tp, "JPEG", quality=80, optimize=True, progressive=True)
    return fp, tp


manifest = {"series": []}

for slug, tag, cat, wq, sq in PLAN:
    print(f"\n=== {slug} ({tag})", flush=True)
    outdir = os.path.join(STAGE, slug)
    os.makedirs(outdir, exist_ok=True)
    cands = []
    seen_hash = set()

    # ---- wallhaven ----
    wh_items = []
    for page in (1, 2):
        r = get("https://wallhaven.cc/api/v1/search", params={
            "q": wq, "categories": "010", "purity": "100",
            "sorting": "relevance", "order": "desc", "page": page,
            "atleast": "900x1400",
        })
        if not r:
            break
        try:
            data = r.json().get("data", [])
        except Exception:
            break
        if not data:
            break
        wh_items.extend(data)
        time.sleep(1.2)
    print(f"  wallhaven hits: {len(wh_items)}", flush=True)

    for it in wh_items:
        if len(cands) >= MAX_PER_SERIES:
            break
        wid = it.get("id", "")
        if wid in used_wh:
            continue
        url = it.get("path")
        if not url or url in used_urls:
            continue
        rw, rh = it.get("dimension_x", 0), it.get("dimension_y", 0)
        if rw < 700 or rh < 900:
            continue
        r = get(url, stream=True)
        if not r:
            continue
        raw = r.content
        h = hashlib.md5(raw).hexdigest()
        if h in seen_hash:
            continue
        key = "wh" + wid
        out = process(raw, key, outdir)
        if not out:
            continue
        seen_hash.add(h)
        used_wh.add(wid)
        tags = [t.get("name", "") for t in (it.get("tags") or []) if t.get("name")]
        cands.append({
            "key": key, "src": "wallhaven", "page": it.get("url", ""),
            "origin": url, "src_tags": tags,
            "colors": it.get("colors", []), "w": rw, "h": rh,
        })
        print(f"   + {key} {rw}x{rh} {','.join(tags[:6])}", flush=True)
        time.sleep(0.4)

    # ---- safebooru fallback ----
    if len(cands) < 16:
        r = get("https://safebooru.org/index.php", params={
            "page": "dapi", "s": "post", "q": "index", "json": "1",
            "tags": sq, "limit": "100",
        })
        posts = []
        if r:
            try:
                posts = r.json()
            except Exception:
                posts = []
        posts.sort(key=lambda p: -(int(p.get("score") or 0)))
        print(f"  safebooru hits: {len(posts)}", flush=True)
        for p in posts:
            if len(cands) >= MAX_PER_SERIES:
                break
            tlist = (p.get("tags") or "").split()
            if BAD & set(tlist):
                continue
            try:
                pw, ph = int(p.get("width") or 0), int(p.get("height") or 0)
            except Exception:
                continue
            if pw < 700 or ph < 900 or ph / max(pw, 1) < 1.15:
                continue
            url = p.get("file_url")
            if not url or url in used_urls:
                continue
            r2 = get(url, stream=True)
            if not r2:
                continue
            raw = r2.content
            h = hashlib.md5(raw).hexdigest()
            if h in seen_hash:
                continue
            key = "sb" + str(p.get("id"))
            out = process(raw, key, outdir)
            if not out:
                continue
            seen_hash.add(h)
            cands.append({
                "key": key, "src": "safebooru", "page": "https://safebooru.org/index.php?page=post&s=view&id=" + str(p.get("id")),
                "origin": url, "src_tags": tlist, "colors": [], "w": pw, "h": ph,
            })
            print(f"   + {key} {pw}x{ph}", flush=True)
            time.sleep(0.4)

    manifest["series"].append({"slug": slug, "tag": tag, "category": cat, "candidates": cands})
    print(f"  staged {len(cands)}", flush=True)

    # ---- contact sheet ----
    if cands:
        cols, cell_w, cell_h = 5, 216, 384
        rows = (len(cands) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), (18, 18, 22))
        d = ImageDraw.Draw(sheet)
        for i, c in enumerate(cands):
            try:
                t = Image.open(os.path.join(outdir, c["key"] + "_thumb.jpg")).resize((cell_w, cell_h))
            except Exception:
                continue
            x, y = (i % cols) * cell_w, (i // cols) * cell_h
            sheet.paste(t, (x, y))
            d.rectangle([x, y, x + 34, y + 18], fill=(0, 0, 0))
            d.text((x + 3, y + 4), str(i + 1), fill=(255, 255, 0))
        sheet.save(os.path.join(SHEETS, f"{slug}.jpg"), "JPEG", quality=82, optimize=True)

json.dump(manifest, open(f"{ROOT}/manifest.json", "w"), indent=1)
print("\nDONE")
for s in manifest["series"]:
    print(f"  {s['slug']:26s} {len(s['candidates'])}")
