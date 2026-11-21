#!/usr/bin/env python3
"""Low-count run v22: candidates from safebooru.org (XML) + yande.re (safe only)."""
import os, io, json, re, time
import requests
from PIL import Image, ImageDraw

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "*/*"}
OUT = "_tmp/lowrun22"
PREV = os.path.join(OUT, "prev6")
os.makedirs(PREV, exist_ok=True)

SERIES = [
    ("quintessential quintuplets", ["5-toubun_no_hanayome", "gotoubun_no_hanayome"]),
    ("a silent voice", ["koe_no_katachi"]),
    ("food wars", ["shokugeki_no_souma"]),
    ("natsume yuujinchou", ["natsume_yuujinchou"]),
    ("yona of the dawn", ["akatsuki_no_yona"]),
    ("oregairu", ["yahari_ore_no_seishun_love_comedy_wa_machigatteiru"]),
    ("the wind rises", ["kaze_tachinu"]),
    ("jigokuraku", ["jigokuraku"]),
    ("kuroko no basket", ["kuroko_no_basuke"]),
    ("fire force", ["enen_no_shouboutai"]),
    ("akame ga kill", ["akame_ga_kiru"]),
    ("k-on", ["k-on!"]),
    ("horimiya", ["horimiya"]),
    ("tokyo revengers", ["tokyo_revengers"]),
    ("solo leveling", ["solo_leveling"]),
    ("seraph of the end", ["owari_no_seraph"]),
    ("made in abyss", ["made_in_abyss"]),
    ("blue exorcist", ["ao_no_exorcist"]),
    ("mashle", ["mashle"]),
    ("nisekoi", ["nisekoi"]),
]

BAD = {"text", "english_text", "watermark", "signature", "artist_name", "speech_bubble", "comic", "4koma",
       "multiple_views", "character_sheet", "translated", "logo", "border", "frame", "letterboxed",
       "twitter_username", "web_address", "dated", "artist_logo", "english_commentary", "bad_id",
       "sketch", "monochrome", "greyscale", "partially_colored", "censored", "manga", "scan", "sample",
       "chibi", "comic_panel", "bikini", "swimsuit", "underwear", "lingerie", "panties", "bra",
       "cleavage", "no_bra", "see_through", "spread_legs", "large_breasts", "huge_breasts", "ass",
       "nude", "naked", "topless", "wet", "bed", "bottomless", "sideboob", "underboob", "photo",
       "photograph", "cosplay", "screencap", "screenshot", "reference_sheet", "upscaled",
       "jpeg_artifacts", "lowres", "real_world_location", "photo_background", "collage", "crossover",
       "vector", "lineart", "line_art", "loli", "comic_book", "cover", "magazine", "poster",
       "abstract", "sample_watermark", "english_text", "artist_request", "highres", "absurdres",
       "pantyshot", "thighhighs", "garter_belt", "stockings", "cum", "cameltoe", "torn_clothes",
       "nipples", "pussy", "sex", "suggestive", "imminent", "breasts", "navel", "midriff",
       "upskirt", "see-through", "tight_clothes", "sweat", "wet_clothes", "bondage", "gag"}
MAXC = 26


def parse_xml(body):
    out = []
    for m in re.finditer(r"<post\s([^>]*)/?>", body):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        out.append(attrs)
    return out


def safebooru(tag, pages=3):
    res = []
    for p in range(pages):
        try:
            r = requests.get("https://safebooru.org/index.php",
                             params={"page": "dapi", "s": "post", "q": "index", "tags": tag,
                                     "limit": 100, "pid": p}, headers=UA, timeout=30)
        except Exception as e:
            print("  ERR sb", type(e).__name__, flush=True)
            break
        if r.status_code != 200:
            print("  HTTP sb", r.status_code, flush=True)
            break
        posts = parse_xml(r.text)
        if not posts:
            break
        for a in posts:
            try:
                w, h = int(a.get("width") or 0), int(a.get("height") or 0)
            except Exception:
                continue
            res.append(dict(site="safebooru", pid=a.get("id"), w=w, h=h,
                            url=a.get("file_url"), prev=a.get("sample_url") or a.get("file_url"),
                            tags=a.get("tags") or "", rating=a.get("rating") or "s"))
        if len(posts) < 100:
            break
        time.sleep(0.4)
    return res


def yande(tag, pages=3):
    res = []
    for p in range(1, pages + 1):
        try:
            r = requests.get("https://yande.re/post.json",
                             params={"tags": tag + " rating:s", "limit": 100, "page": p}, headers=UA, timeout=40)
        except Exception as e:
            print("  ERR yd", type(e).__name__, flush=True)
            break
        if r.status_code != 200:
            print("  HTTP yd", r.status_code, flush=True)
            break
        try:
            js = r.json()
        except Exception:
            break
        if not isinstance(js, list) or not js:
            break
        for p2 in js:
            res.append(dict(site="yande", pid=p2.get("id"), w=p2.get("width") or 0, h=p2.get("height") or 0,
                            url=p2.get("file_url"), prev=p2.get("sample_url") or p2.get("jpeg_url") or p2.get("file_url"),
                            tags=p2.get("tags") or "", rating=p2.get("rating") or "s"))
        if len(js) < 100:
            break
        time.sleep(1.0)
    return res


cands = []
for app, tags in SERIES:
    pool, seen = [], set()
    for t in tags:
        for src in (safebooru, yande):
            for p in src(t):
                k = (p["site"], p["pid"])
                if k in seen:
                    continue
                seen.add(k)
                pool.append(p)
    print("== %s pool=%d" % (app, len(pool)), flush=True)

    kept = []
    for p in pool:
        w, h = p["w"], p["h"]
        if not w or not h or not p.get("url") or not p.get("prev"):
            continue
        if p.get("rating") not in ("s", None):
            continue
        r = h / w
        if r < 1.2:          # portrait only
            continue
        if h < 1300 or w < 700:
            continue
        if set((p["tags"] or "").split()) & BAD:
            continue
        kept.append(p)
    kept.sort(key=lambda p: (0 if p["site"] == "safebooru" else 1, -(p["h"])))
    print("   kept=%d" % len(kept), flush=True)

    idx = 0
    slug = "".join(c if c.isalnum() else "-" for c in app)[:26]
    for p in kept:
        if idx >= MAXC:
            break
        try:
            r = requests.get(p["prev"], headers=dict(UA, Referer="https://" + p["site"] + "/"), timeout=40)
            if r.status_code != 200 or len(r.content) < 3000:
                continue
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
        except Exception:
            continue
        if im.height / im.width < 1.2:
            continue
        name = "%s_%02d" % (slug, idx)
        im.save(os.path.join(PREV, name + ".jpg"), "JPEG", quality=85)
        cands.append(dict(series=app, idx=idx, name=name, site=p["site"], pid=p["pid"],
                          w=p["w"], h=p["h"], url=p["url"], prev=p["prev"], tags=p["tags"]))
        idx += 1
        time.sleep(0.15)

json.dump(cands, open(os.path.join(OUT, "cand6.json"), "w"), indent=1)
print("total candidates:", len(cands), flush=True)

by = {}
for c in cands:
    by.setdefault(c["series"], []).append(c)
for s, items in by.items():
    slug = "".join(c if c.isalnum() else "-" for c in s)[:26]
    for part in range(0, len(items), 15):
        chunk = items[part:part + 15]
        cols, cw, ch = 5, 260, 470
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cw, rows * ch), (16, 16, 20))
        d = ImageDraw.Draw(sheet)
        for i, c in enumerate(chunk):
            p = Image.open(os.path.join(PREV, c["name"] + ".jpg")).convert("RGB")
            p.thumbnail((cw - 8, ch - 20), Image.LANCZOS)
            x = (i % cols) * cw + (cw - p.width) // 2
            y = (i // cols) * ch + 18
            sheet.paste(p, (x, y))
            d.text(((i % cols) * cw + 5, 4 + (i // cols) * ch), "#%d" % c["idx"], fill=(255, 235, 0))
        sheet.save(os.path.join(OUT, "sh6_%s_%d.jpg" % (slug, part // 15)), "JPEG", quality=90)
    print("sheet", s, len(items), flush=True)
