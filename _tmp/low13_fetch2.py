#!/usr/bin/env python3
"""Low-count run v13b: second pass for thin series."""
import os, io, json, time, re
import requests
from PIL import Image, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json,text/plain,*/*"}

# (json series tag, alt tag, [booru queries])
SERIES = [
    ("initial d", "initial d fourth stage", ["initial_d", "initial_d_(series)", "fujiwara_takumi", "ae86"]),
    ("kaiju no 8", "kaijuu 8-gou", ["kaijuu_8-gou", "kaiju_no._8", "hibino_kafka", "shinomiya_kikoru"]),
    ("kaguya-sama", "kaguya-sama wa kokurasetai", ["kaguya-sama_wa_kokurasetai", "kaguya-sama_wa_kokuraseru", "kaguya-sama", "shinomiya_kaguya", "shirogane_miyuki"]),
    ("nausicaa", "nausicaa of the valley of the wind", ["nausicaa", "kaze_no_tani_no_nausicaa", "nausicaa_of_the_valley_of_the_wind"]),
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
       "vector", "lineart", "line_art", "sketchbook", "gun", "blood", "gore", "solo_focus_", "logo_",
       "tattoo", "child", "loli", "shota", "toddler", "baby"}

OUT = "_tmp/prev13b"
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
                time.sleep(1.0)
                return r
            print("  HTTP", r.status_code, url, flush=True)
        except Exception as e:
            print("  ERR", type(e).__name__, flush=True)
        time.sleep(3)
    return None


def parse_site(base, js, tag):
    out = []
    if not isinstance(js, list):
        return out
    for p in js:
        if "tag_string" in p:  # danbooru / safebooru
            out.append(dict(site=base, id=p.get("id"), score=p.get("score") or 0,
                            w=p.get("image_width") or p.get("width") or 0,
                            h=p.get("image_height") or p.get("height") or 0,
                            url=p.get("file_url") or p.get("large_file_url"),
                            prev=p.get("sample_url") or p.get("large_file_url") or p.get("file_url"),
                            tags=p.get("tag_string") or "", rating=p.get("rating")))
        else:  # moebooru (konachan / yande.re)
            out.append(dict(site=base, id=p.get("id"), score=p.get("score") or 0,
                            w=p.get("width") or 0, h=p.get("height") or 0,
                            url=p.get("file_url"),
                            prev=p.get("sample_url") or p.get("jpeg_url") or p.get("file_url"),
                            tags=p.get("tags") or "", rating=p.get("rating")))
    return out


def fetch_site(base, tag):
    out = []
    for page in (1, 2):
        params = {"tags": tag, "limit": 100, "page": page}
        if "danbooru" in base:
            params["tags"] = tag + " rating:general"
        r = get(base, params)
        if not r:
            break
        try:
            js = r.json()
        except Exception:
            break
        got = parse_site(base, js, tag)
        if not got:
            break
        out += got
        if len(js) < 100:
            break
    return out


SOURCES = ["https://safebooru.donmai.us/posts.json",
           "https://konachan.net/post.json",
           "https://yande.re/post.json",
           "https://danbooru.donmai.us/posts.json"]

for name, alt, tags in SERIES:
    pool = []
    for t in tags:
        for base in SOURCES:
            if len(pool) >= 220:
                break
            pool += fetch_site(base, t)
    print("== %s: pool=%d" % (name, len(pool)), flush=True)
    seen, kept = set(), []
    pool.sort(key=lambda p: -(p["score"] or 0))
    for p in pool:
        key = (p["site"], p["id"])
        if key in seen:
            continue
        seen.add(key)
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
        if set(p["tags"].split()) & BAD:
            continue
        if p.get("rating") not in ("s", "g", "sensitive", None):
            continue
        kept.append(p)
    print("   valid=%d" % len(kept), flush=True)

    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    n = 0
    for p in kept:
        if n >= 20:
            break
        try:
            r = requests.get(p["prev"], headers=UA, timeout=40)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            if im.size[0] < 500:
                continue
            fn = "%s_%02d.jpg" % (slug, n)
            render(im).save(os.path.join(OUT, fn), "JPEG", quality=82, optimize=True)
            cands.append(dict(series=name, alt=alt, file=fn, pid=p["id"], site=p["site"],
                              score=p["score"], w=p["w"], h=p["h"], url=p["url"], tags=p["tags"][:400]))
            n += 1
        except Exception as e:
            print("   dl err", p.get("id"), type(e).__name__, flush=True)
        time.sleep(0.3)
    print("   previews=%d" % n, flush=True)

json.dump(cands, open("_tmp/candlow13b.json", "w"), indent=1)
print("TOTAL candidates", len(cands), flush=True)
