#!/usr/bin/env python3
"""Low-count run v12: final top-up round for two more series."""
import os, io, json, time, re
import requests
from PIL import Image, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json,text/plain,*/*",
      "Referer": "https://konachan.net/"}

SERIES = [
    ("my neighbor totoro", ["tonari_no_totoro", "totoro"], set()),
    ("cyberpunk edgerunners", ["cyberpunk_edgerunners", "cyberpunk"], set()),
    ("bleach", ["bleach"], set()),
    ("madoka magica", ["mahou_shoujo_madoka_magica"], set()),
    ("oshi no ko", ["oshi_no_ko"], set()),
    ("fate stay night", ["fate_stay_night", "fate_(series)"], set()),
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
       "vector", "lineart", "line_art"}

OUT = "_tmp/prevlow12"
os.makedirs(OUT, exist_ok=True)
cands = []


def render(im, size=(360, 640)):
    w, h = im.size
    r = h / w
    tw, th = size
    t = 16 / 9
    if r > 2.2:
        bg = ImageOps.fit(im, (tw, th), method=Image.LANCZOS).filter(ImageFilter.GaussianBlur(22))
        fg = im.copy()
        fg.thumbnail((tw, th), Image.LANCZOS)
        bg.paste(fg, ((tw - fg.width) // 2, (th - fg.height) // 2))
        return bg
    if r > t:
        nh = int(w * t)
        y = int((h - nh) * 0.04)
        return im.crop((0, y, w, y + nh))
    nw = int(h / t)
    x = (w - nw) // 2
    return im.crop((x, 0, x + nw, h))


def get(url, params, timeout=25):
    for _ in range(2):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout)
            if r.status_code == 200:
                time.sleep(1.2)
                return r
            print("  HTTP", r.status_code, url, flush=True)
        except Exception as e:
            print("  ERR", type(e).__name__, flush=True)
        time.sleep(3)
    return None


def fetch_site(base, tag):
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
            out.append(dict(site=base, id=p.get("id"), score=p.get("score") or 0,
                            w=p.get("width") or 0, h=p.get("height") or 0, url=p.get("file_url"),
                            prev=p.get("sample_url") or p.get("jpeg_url") or p.get("file_url"),
                            tags=p.get("tags") or "", rating=p.get("rating")))
        if len(js) < 100:
            break
    return out


for name, tags, ignore in SERIES:
    bad = BAD - ignore
    pool = []
    for t in tags:
        pool += fetch_site("https://konachan.net/post.json", t)
    if len(pool) < 25:
        for t in tags:
            pool += fetch_site("https://yande.re/post.json", t)
    print("== %s: pool=%d" % (name, len(pool)), flush=True)
    seen, kept = set(), []
    pool.sort(key=lambda p: -(p["score"] or 0))
    for p in pool:
        if p["id"] in seen:
            continue
        seen.add(p["id"])
        w, h = p["w"], p["h"]
        if not w or not h or not p.get("url"):
            continue
        r = h / w
        if r >= 1.2:
            if h < 1300 or w < 700:
                continue
        elif r <= 0.8:
            if w < 1800:
                continue
        else:
            continue
        if set(p["tags"].split()) & bad:
            continue
        if p.get("rating") not in ("s", None):
            continue
        kept.append(p)
    print("   valid=%d" % len(kept), flush=True)

    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    n = 0
    for p in kept:
        if n >= 18:
            break
        try:
            r = requests.get(p["prev"], headers=UA, timeout=30)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            fn = "%s_%02d.jpg" % (slug, n)
            render(im).save(os.path.join(OUT, fn), "JPEG", quality=82, optimize=True)
            cands.append(dict(series=name, file=fn, pid=p["id"], site=p["site"],
                              score=p["score"], w=p["w"], h=p["h"], url=p["url"], tags=p["tags"][:400]))
            n += 1
        except Exception as e:
            print("   dl err", p.get("id"), type(e).__name__, flush=True)
        time.sleep(0.3)
    print("   previews=%d" % n, flush=True)

json.dump(cands, open("_tmp/candlow12.json", "w"), indent=1)
print("TOTAL candidates", len(cands), flush=True)
