#!/usr/bin/env python3
"""Low-count run v10: konachan.net + yande.re candidates (wallpaper sites, series tags)."""
import os, io, json, time, re
import requests
from PIL import Image, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json,text/plain,*/*",
      "Referer": "https://konachan.net/"}

SERIES = [
    ("initial d", ["initial_d", "ae86"]),
    ("pokemon", ["pokemon"]),
    ("detective conan", ["detective_conan"]),
    ("clannad", ["clannad"]),
    ("dragon ball super", ["dragon_ball_super", "dragon_ball"]),
    ("neon genesis evangelion", ["neon_genesis_evangelion"]),
    ("konosuba", ["kono_subarashii_sekai_ni_shukufuku_wo!"]),
    ("seven deadly sins", ["nanatsu_no_taizai"]),
    ("nausicaa", ["nausicaa_of_the_valley_of_the_wind"]),
    ("berserk", ["berserk"]),
    ("howls moving castle", ["howl's_moving_castle"]),
    ("kaiju no 8", ["kaijuu_8_gou"]),
]

BAD = {"text", "english_text", "watermark", "signature", "artist_name", "speech_bubble", "comic", "4koma",
       "multiple_views", "character_sheet", "translated", "logo", "border", "frame", "letterboxed",
       "twitter_username", "web_address", "dated", "artist_logo", "english_commentary", "bad_id",
       "sketch", "monochrome", "greyscale", "partially_colored", "gun", "mecha", "vehicle", "blood",
       "gore", "censored", "manga", "scan", "sample", "food", "chibi", "comic_panel", "bikini",
       "swimsuit", "underwear", "lingerie", "panties", "bra", "cleavage", "no_bra", "see_through",
       "spread_legs", "large_breasts", "huge_breasts", "ass", "nude", "naked", "topless",
       "wet", "bed", "bottomless", "sideboob", "underboob", "photo", "photograph", "cosplay",
       "screencap", "screenshot", "reference_sheet", "upscaled", "jpeg_artifacts", "lowres",
       "real_world_location", "photo_background", "collage", "crossover", "multiple_girls",
       "multiple_boys", "vector", "lineart", "line_art", "sketch"}

OUT = "_tmp/prevlow10"
os.makedirs(OUT, exist_ok=True)
cands = []


def render(im, size=(360, 640)):
    w, h = im.size
    r = h / w
    tw, th = size
    t = 9 / 16
    if r > 2.05:
        bg = ImageOps.fit(im, (tw, th), method=Image.LANCZOS).filter(ImageFilter.GaussianBlur(22))
        fg = im.copy()
        fg.thumbnail((tw, th), Image.LANCZOS)
        bg.paste(fg, ((tw - fg.width) // 2, (th - fg.height) // 2))
        return bg
    if r > t:
        nh = int(w / t)
        y = int((h - nh) * (0.04 if r >= 1.55 else 0.18))
        return im.crop((0, y, w, y + nh))
    nw = int(h * t)
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
                            w=p.get("width") or 0, h=p.get("height") or 0,
                            url=p.get("file_url"), jpg=p.get("jpeg_url") or p.get("file_url"),
                            prev=p.get("sample_url") or p.get("jpeg_url") or p.get("file_url"),
                            tags=p.get("tags") or "", rating=p.get("rating")))
        if len(js) < 100:
            break
    return out


def ok(p):
    w, h = p["w"], p["h"]
    if not w or not h or not p.get("url"):
        return False
    r = h / w
    if r >= 1.2:
        if h < 1300 or w < 700:
            return False
    elif r <= 0.8:
        if w < 1800:
            return False
    else:
        return False
    tg = set(p["tags"].split())
    if tg & BAD:
        return False
    if p.get("rating") not in ("s", None):
        return False
    return True


for name, tags in SERIES:
    pool = []
    for t in tags:
        pool += fetch_site("https://konachan.net/post.json", t)
    if len(pool) < 30:
        for t in tags:
            pool += fetch_site("https://yande.re/post.json", t)
    print("== %s: pool=%d" % (name, len(pool)), flush=True)
    seen, kept = set(), []
    pool.sort(key=lambda p: -(p["score"] or 0))
    for p in pool:
        if p["id"] in seen:
            continue
        seen.add(p["id"])
        if ok(p):
            kept.append(p)
    print("   valid=%d" % len(kept), flush=True)

    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    n = 0
    for p in kept:
        if n >= 24:
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

json.dump(cands, open("_tmp/candlow10.json", "w"), indent=1)
print("TOTAL candidates", len(cands), flush=True)
