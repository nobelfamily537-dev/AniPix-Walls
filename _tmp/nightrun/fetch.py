#!/usr/bin/env python3
"""Night run: preview fetch. wallhaven -> anime-pictures fallback."""
import os, io, json, time, re
import requests
from PIL import Image, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json,text/plain,*/*"}

SERIES = [
    ("beastars",        ["beastars", "legoshi", "haru beastars"]),
    ("dorohedoro",      ["dorohedoro", "caiman", "nikaido"]),
    ("samurai champloo",["samurai champloo", "mugen", "jin samurai champloo"]),
    ("tower of god",    ["tower of god", "bam tower of god", "khun"]),
    ("hellsing",        ["hellsing", "alucard", "seras victoria"]),
    ("yu yu hakusho",   ["yu yu hakusho", "hiei", "kurama"]),
    ("gachiakuta",      ["gachiakuta", "rudo", "enjin"]),
    ("mushishi",        ["mushishi", "ginko"]),
    ("nichijou",        ["nichijou", "aioi yuuko", "naganohara mio"]),
    ("shangri-la frontier", ["shangri la frontier", "sunraku"]),
    ("undead unluck",   ["undead unluck", "fuuko izumo", "andy undead unluck"]),
    ("death parade",    ["death parade", "decim"]),
    ("slam dunk",       ["slam dunk", "sakuragi", "rukawa"]),
    ("akira",           ["akira anime", "kaneda", "shotaro kaneda"]),
    ("world trigger",   ["world trigger", "yuma kuga", "jin yuichi"]),
    ("baki",            ["baki", "hanma baki", "yujiro"]),
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
       "vector", "lineart", "line_art", "parody", "meme", "sign", "mosaic_censoring", "bar_censor"}

OUT = "_tmp/nightrun/pv"
os.makedirs(OUT, exist_ok=True)
diag = {}


def render(im, size=(540, 960)):
    w, h = im.size
    r = h / w
    t = 16 / 9
    if r > 2.2:
        bg = ImageOps.fit(im, size, method=Image.LANCZOS).filter(ImageFilter.GaussianBlur(22))
        fg = im.copy()
        fg.thumbnail(size, Image.LANCZOS)
        bg.paste(fg, ((size[0] - fg.width) // 2, (size[1] - fg.height) // 2))
        return bg
    if r > t:
        nh = int(w * t)
        y = int((h - nh) * 0.05)
        return im.crop((0, y, w, y + nh))
    nw = int(h / t)
    x = (w - nw) // 2
    return im.crop((x, 0, x + nw, h))


def get(url, params=None, timeout=35):
    for _ in range(2):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout)
            if r.status_code == 200:
                time.sleep(0.7)
                return r
            print("  HTTP", r.status_code, url, flush=True)
        except Exception as e:
            print("  ERR", type(e).__name__, str(e)[:90], flush=True)
        time.sleep(2)
    return None


def wallhaven(q, page=1):
    out = []
    r = get("https://wallhaven.cc/api/v1/search",
            {"q": q, "categories": "010", "purity": "100", "ratios": "9x16",
             "atleast": "1080x1920", "sorting": "favorites", "order": "desc", "page": page})
    if not r:
        return out
    try:
        js = r.json()
    except Exception as e:
        diag.setdefault("wh_parse", str(e)[:120])
        return out
    if "data" not in js:
        diag.setdefault("wh_keys", list(js)[:8])
        return out
    for p in js["data"]:
        out.append(dict(site="wallhaven", id=p.get("id"), score=0,
                        w=p.get("dimension_x") or 0, h=p.get("dimension_y") or 0,
                        url=p.get("path"), prev=p.get("thumbs", {}).get("large") or p.get("path"),
                        tags=" ".join(p.get("tags", []) and [t.get("name", "") for t in p["tags"]] or []),
                        rating="s"))
    return out


def animepictures(tag):
    out = []
    r = get("https://anime-pictures.net/posts",
            {"api": "1", "search_tag": tag, "page": 0, "lang": "en"})
    if not r:
        return out
    try:
        js = r.json()
    except Exception as e:
        diag.setdefault("ap_parse", str(e)[:120])
        return out
    posts = js.get("posts") or []
    if posts:
        diag.setdefault("ap_sample", list(posts[0])[:15])
    for p in posts:
        out.append(dict(site="anime-pictures", id=p.get("id"), score=p.get("rating") or 0,
                        w=p.get("width") or 0, h=p.get("height") or 0,
                        url=p.get("file_url"), prev=p.get("big_preview_url") or p.get("preview_url") or p.get("file_url"),
                        tags=" ".join([t for t in (p.get("tags") or []) if isinstance(t, str)]),
                        rating="s"))
    return out


cands = []
summary = {}
for name, tags in SERIES:
    pool = []
    for t in tags:
        got = wallhaven(t)
        print("  wallhaven %s -> %d" % (t, len(got)), flush=True)
        pool += got
    if len(pool) < 12:
        for t in tags:
            got = animepictures(t.replace(" ", "_"))
            print("  anime-pictures %s -> %d" % (t, len(got)), flush=True)
            pool += got
    reasons = {"landscape": 0, "small": 0, "bad": 0, "nodata": 0}
    seen, kept = set(), []
    pool.sort(key=lambda p: -(p["score"] or 0))
    for p in pool:
        if p["id"] in seen:
            continue
        seen.add(p["id"])
        w, h = p["w"], p["h"]
        if not w or not h or not p.get("url"):
            reasons["nodata"] += 1
            continue
        r = h / w
        if r < 1.15:
            reasons["landscape"] += 1
            continue
        if h < 1300 or w < 700:
            reasons["small"] += 1
            continue
        tg = set(p["tags"].split())
        if tg & BAD:
            reasons["bad"] += 1
            continue
        kept.append(p)
    summary[name] = dict(pool=len(pool), valid=len(kept), reasons=reasons)
    print("== %s pool=%d valid=%d %s" % (name, len(pool), len(kept), reasons), flush=True)
    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    n = 0
    for p in kept:
        if n >= 10:
            break
        try:
            r = requests.get(p["prev"], headers=UA, timeout=45)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            fn = "%s_%02d.jpg" % (slug, n)
            render(im).save(os.path.join(OUT, fn), "JPEG", quality=82, optimize=True)
            cands.append(dict(series=name, slug=slug, file=fn, pid=p["id"], site=p["site"],
                              score=p["score"], w=p["w"], h=p["h"], url=p["url"],
                              tags=p["tags"][:600]))
            n += 1
        except Exception as e:
            print("   dl err", p.get("id"), type(e).__name__, str(e)[:60], flush=True)
        time.sleep(0.2)
    print("   previews=%d" % n, flush=True)

json.dump(dict(cands=cands, summary=summary, diag=diag), open("_tmp/nightrun/candidates.json", "w"), indent=1)
print("TOTAL previews", len(cands), "DIAG", diag, flush=True)
