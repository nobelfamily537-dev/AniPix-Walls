#!/usr/bin/env python3
"""Night run 21 Nov: preview fetch for anime with zero tag coverage."""
import os, io, json, time, re
import requests
from PIL import Image, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json,text/plain,*/*",
      "Referer": "https://konachan.net/"}

SERIES = [
    ("beastars",        ["beastars", "legoshi", "haru_(beastars)", "louis_(beastars)"]),
    ("dorohedoro",      ["dorohedoro", "caiman_(dorohedoro)", "nikaido", "noi_(dorohedoro)"]),
    ("samurai champloo",["samurai_champloo", "mugen_(samurai_champloo)", "jin_(samurai_champloo)", "fuu_(samurai_champloo)"]),
    ("tower of god",    ["tower_of_god", "bam_(tower_of_god)", "khun_aguero_agnis", "rachel_(tower_of_god)"]),
    ("hellsing",        ["hellsing", "alucard_(hellsing)", "seras_victoria"]),
    ("yu yu hakusho",   ["yu_yu_hakusho", "urameshi_yusuke", "kurama_(yu_yu_hakusho)", "hiei"]),
    ("gachiakuta",      ["gachiakuta", "rudo_(gachiakuta)", "enjin_(gachiakuta)"]),
    ("mushishi",        ["mushishi", "ginko_(mushishi)"]),
    ("nichijou",        ["nichijou", "aioi_yuuko", "naganohara_mio"]),
    ("shangri-la frontier", ["shangri-la_frontier", "sunraku"]),
    ("undead unluck",   ["undead_unluck", "fuuko_izumo", "andy_(undead_unluck)"]),
    ("death parade",    ["death_parade", "decim"]),
    ("slam dunk",       ["slam_dunk", "sakuragi_hanamichi", "rukawa_kaede"]),
    ("akira",           ["akira_(manga)", "kaneda_shotaro", "shikishima_tetsuo"]),
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
       "vector", "lineart", "line_art", "fate_(series)", "pokemon", "gundam"}

OUT = "_tmp/nightrun/pv"
os.makedirs(OUT, exist_ok=True)


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


def get(url, params, timeout=25):
    for _ in range(2):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout)
            if r.status_code == 200:
                time.sleep(1.1)
                return r
            print("  HTTP", r.status_code, flush=True)
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
                            url=p.get("file_url"),
                            prev=p.get("sample_url") or p.get("jpeg_url") or p.get("file_url"),
                            tags=p.get("tags") or "", rating=p.get("rating")))
        if len(js) < 100:
            break
    return out


cands = []
summary = {}
for name, tags in SERIES:
    pool = []
    for t in tags:
        got = fetch_site("https://konachan.net/post.json", t)
        print("  tag %s -> %d" % (t, len(got)), flush=True)
        pool += got
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
        if r < 1.2:
            continue
        if h < 1400 or w < 760:
            continue
        tg = set(p["tags"].split())
        if tg & BAD:
            continue
        if p.get("rating") not in ("s", None):
            continue
        if len(tg) > 120:
            continue
        kept.append(p)
    summary[name] = dict(pool=len(pool), valid=len(kept))
    print("== %s pool=%d valid=%d" % (name, len(pool), len(kept)), flush=True)
    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    n = 0
    for p in kept:
        if n >= 10:
            break
        try:
            r = requests.get(p["prev"], headers=UA, timeout=40)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            fn = "%s_%02d.jpg" % (slug, n)
            render(im).save(os.path.join(OUT, fn), "JPEG", quality=82, optimize=True)
            cands.append(dict(series=name, slug=slug, file=fn, pid=p["id"], site=p["site"],
                              score=p["score"], w=p["w"], h=p["h"], url=p["url"],
                              tags=p["tags"][:500]))
            n += 1
        except Exception as e:
            print("   dl err", p.get("id"), type(e).__name__, flush=True)
        time.sleep(0.3)
    print("   previews=%d" % n, flush=True)

json.dump(dict(cands=cands, summary=summary), open("_tmp/nightrun/candidates.json", "w"), indent=1)
print("TOTAL previews", len(cands), flush=True)
