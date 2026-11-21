#!/usr/bin/env python3
"""Low-count run v22: gather candidate art for the emptiest series.

Fetches candidates from konachan.net / yande.re / danbooru, filters on booru
tags + resolution + rating, writes review previews, per-series contact sheets
and cand.json. No wallpapers are added here - the picks are reviewed first.
"""
import os, io, json, time, hashlib
import requests
from PIL import Image, ImageDraw

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json,text/plain,*/*"}

OUT = "_tmp/lowrun22"
PREV = os.path.join(OUT, "prev")
os.makedirs(PREV, exist_ok=True)

# (app tag, booru tag list, danbooru tag)
SERIES = [
    ("quintessential quintuplets", ["gotoubun_no_hanayome"], "gotoubun_no_hanayome"),
    ("a silent voice", ["koe_no_katachi"], "koe_no_katachi"),
    ("food wars", ["shokugeki_no_souma"], "shokugeki_no_souma"),
    ("natsume yuujinchou", ["natsume_yuujinchou"], "natsume_yuujinchou"),
    ("yona of the dawn", ["akatsuki_no_yona"], "akatsuki_no_yona"),
    ("oregairu", ["yahari_ore_no_seishun_love_comedy_wa_machigatteiru"], "yahari_ore_no_seishun_love_comedy_wa_machigatteiru"),
    ("the wind rises", ["kaze_tachinu"], "kaze_tachinu"),
    ("jigokuraku", ["jigokuraku"], "jigokuraku"),
    ("kuroko no basket", ["kuroko_no_basuke"], "kuroko_no_basuke"),
    ("fire force", ["enen_no_shouboutai"], "enen_no_shouboutai"),
]

BAD = {"text", "english_text", "watermark", "signature", "artist_name", "speech_bubble", "comic", "4koma",
       "multiple_views", "character_sheet", "translated", "logo", "border", "frame", "letterboxed",
       "twitter_username", "web_address", "dated", "artist_logo", "english_commentary", "bad_id",
       "sketch", "monochrome", "greyscale", "partially_colored", "censored", "manga", "scan", "sample",
       "food", "chibi", "comic_panel", "bikini", "swimsuit", "underwear", "lingerie", "panties", "bra",
       "cleavage", "no_bra", "see_through", "spread_legs", "large_breasts", "huge_breasts", "ass",
       "nude", "naked", "topless", "wet", "bed", "bottomless", "sideboob", "underboob", "photo",
       "photograph", "cosplay", "screencap", "screenshot", "reference_sheet", "upscaled",
       "jpeg_artifacts", "lowres", "real_world_location", "photo_background", "collage", "crossover",
       "vector", "lineart", "line_art", "loli", "child", "male_focus_only", "guys_only",
       "1boy", "multiple_boys", "comic_book", "cover", "magazine", "poster", "abstract"}


def get(url, params, timeout=30):
    for _ in range(2):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout)
            if r.status_code == 200:
                time.sleep(1.1)
                return r
            print("  HTTP", r.status_code, url, flush=True)
        except Exception as e:
            print("  ERR", type(e).__name__, url, flush=True)
        time.sleep(3)
    return None


def fetch_booru(base, tag):
    out = []
    for page in (1, 2):
        r = get(base, {"tags": tag, "limit": 100, "page": page})
        if not r:
            break
        try:
            js = r.json()
        except Exception:
            break
        if not isinstance(js, list) or not js:
            break
        for p in js:
            out.append(dict(site=base, pid=p.get("id"), score=p.get("score") or 0,
                            w=p.get("width") or 0, h=p.get("height") or 0,
                            url=p.get("file_url"), tags=p.get("tags") or "",
                            rating=p.get("rating")))
        if len(js) < 100:
            break
    return out


def fetch_danbooru(tag):
    out = []
    r = get("https://danbooru.donmai.us/posts.json",
            {"tags": tag + " rating:general", "limit": 100})
    if not r:
        return out
    try:
        js = r.json()
    except Exception:
        return out
    for p in js:
        url = p.get("file_url")
        if not url:
            continue
        out.append(dict(site="https://danbooru.donmai.us", pid=p.get("id"),
                        score=p.get("score") or 0, w=p.get("image_width") or 0,
                        h=p.get("image_height") or 0, url=url,
                        tags=p.get("tag_string") or "", rating="s"))
    return out


def usable(p):
    w, h = p["w"], p["h"]
    if not w or not h or not p.get("url"):
        return False
    if p.get("rating") not in ("s", None):
        return False
    r = h / w
    if r >= 1.25:
        if h < 1400 or w < 800:
            return False
    elif r <= 0.8:
        if w < 1700:
            return False
    else:
        return False
    if set((p["tags"] or "").split()) & BAD:
        return False
    return True


cands = []
for app_tag, booru_tags, dtag in SERIES:
    pool = []
    for t in booru_tags:
        pool += fetch_booru("https://konachan.net/post.json", t)
    if len(pool) < 40:
        for t in booru_tags:
            pool += fetch_booru("https://yande.re/post.json", t)
    if len(pool) < 40:
        pool += fetch_danbooru(dtag)
    pool.sort(key=lambda p: -(p["score"] or 0))
    seen, kept = set(), []
    for p in pool:
        key = (p["site"], p["pid"])
        if key in seen:
            continue
        seen.add(key)
        if usable(p):
            kept.append(p)
        if len(kept) >= 18:
            break
    print("== %s pool=%d kept=%d" % (app_tag, len(pool), len(kept)), flush=True)

    idx = 0
    for p in kept:
        try:
            r = requests.get(p["url"], headers=UA, timeout=60)
            if r.status_code != 200 or len(r.content) < 40000:
                continue
            im = Image.open(io.BytesIO(r.content))
            im.load()
            if im.width < 800 or im.height < 1100:
                continue
            im = im.convert("RGB")
        except Exception as e:
            print("  skip", type(e).__name__, p["pid"], flush=True)
            continue
        slug = "".join(c if c.isalnum() else "-" for c in app_tag)[:28]
        name = "%s_%02d" % (slug, idx)
        prev = im.copy()
        prev.thumbnail((420, 420 * 3), Image.LANCZOS)
        prev.save(os.path.join(PREV, name + ".jpg"), "JPEG", quality=82)
        cands.append(dict(series=app_tag, idx=idx, name=name, site=p["site"], pid=p["pid"],
                          score=p["score"], w=im.width, h=im.height,
                          url=p["url"], tags=p["tags"]))
        idx += 1
        time.sleep(0.4)

json.dump(cands, open(os.path.join(OUT, "cand.json"), "w"), indent=1)
print("total candidates:", len(cands), flush=True)

# contact sheets: 4 cols, labelled
by_series = {}
for c in cands:
    by_series.setdefault(c["series"], []).append(c)
for s, items in by_series.items():
    cols, cw, ch = 4, 280, 498
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cw, rows * ch), (24, 24, 28))
    d = ImageDraw.Draw(sheet)
    for i, c in enumerate(items):
        p = Image.open(os.path.join(PREV, c["name"] + ".jpg")).convert("RGB")
        p.thumbnail((cw - 8, ch - 22), Image.LANCZOS)
        x = (i % cols) * cw + (cw - p.width) // 2
        y = (i // cols) * ch + 20
        sheet.paste(p, (x, y))
        d.text(((i % cols) * cw + 6, 4 + (i // cols) * ch), "#%d" % c["idx"], fill=(255, 255, 0))
    slug = "".join(c if c.isalnum() else "-" for c in s)[:28]
    sheet.save(os.path.join(OUT, "sheet_%s.jpg" % slug), "JPEG", quality=88)
    print("sheet", s, len(items), flush=True)
