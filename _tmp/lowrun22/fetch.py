#!/usr/bin/env python3
"""Low-count run 22 - stage 1: pull candidates from boorus and render 9:16 previews."""
import os, io, json, time, re, hashlib
import requests
from PIL import Image, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json,text/plain,*/*",
      "Referer": "https://konachan.net/"}

BAD = {"text","english_text","watermark","signature","artist_name","speech_bubble","comic","4koma",
 "multiple_views","character_sheet","translated","logo","border","frame","letterboxed","twitter_username",
 "web_address","dated","artist_logo","english_commentary","bad_id","sketch","monochrome","greyscale",
 "partially_colored","censored","manga","scan","sample","food","chibi","comic_panel","bikini","swimsuit",
 "underwear","lingerie","panties","bra","cleavage","no_bra","see_through","spread_legs","large_breasts",
 "huge_breasts","ass","nude","naked","topless","wet","bed","bottomless","sideboob","underboob","photo",
 "photograph","cosplay","screencap","screenshot","reference_sheet","upscaled","jpeg_artifacts","lowres",
 "real_world_location","photo_background","collage","crossover","vector","lineart","line_art","3d",
 "realistic","photo-referenced","sketchbook","doujin","book","magazine","poster","calendar","cover",
 "wallpaper_(medium)","render","cgi","ai-generated","ai_assisted","ai_generated","tracing","sketch_page",
 "censor_bar","bar_censor","steam","mosaic_censoring","personification","gun","military","mecha"}

OUT = "_tmp/lowrun22/preview"
os.makedirs(OUT, exist_ok=True)
picks = json.load(open("_tmp/lowrun22/picks.json"))


def render(im, size=(420, 746)):
    """Crop to 9:16 and resize to preview size."""
    w, h = im.size
    r = h / w
    tw, th = size
    t = th / tw  # 1.776
    if r > t:
        nw = int(h / t)
        x = (w - nw) // 2
        im = im.crop((x, 0, x + nw, h))
    else:
        nh = int(w * t)
        y = int((h - nh) * 0.45)
        im = im.crop((0, y, w, y + nh))
    return im.resize(size, Image.LANCZOS)


def get(url, params):
    for _ in range(2):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=30)
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
    for page in (1, 2, 3):
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
                            url=p.get("file_url"), prev=p.get("jpeg_url") or p.get("sample_url") or p.get("file_url"),
                            tags=p.get("tags") or "", rating=p.get("rating")))
        if len(js) < 100:
            break
    return out


cands = []
for pk in picks:
    name, slug = pk["series"], pk["slug"]
    pool = []
    for t in pk["booru"]:
        pool += fetch_site("https://konachan.net/post.json", t)
    print("== %s pool=%d" % (name, len(pool)), flush=True)
    if len(pool) < 30:
        for t in pk["booru"]:
            pool += fetch_site("https://yande.re/post.json", t)
        print("   +yande pool=%d" % len(pool), flush=True)

    seen, kept = set(), []
    for p in sorted(pool, key=lambda p: -(p["score"] or 0)):
        if p["id"] in seen:
            continue
        seen.add(p["id"])
        w, h = p["w"], p["h"]
        if not w or not h or not p.get("url"):
            continue
        if w < 950 or h < 1500:
            continue
        if set(p["tags"].split()) & BAD:
            continue
        if p.get("rating") not in ("s", None):
            continue
        kept.append(p)
    print("   valid=%d" % len(kept), flush=True)

    n = 0
    for p in kept:
        if n >= 16:
            break
        try:
            r = requests.get(p["prev"], headers=UA, timeout=40)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            fn = "%s_%02d.jpg" % (slug, n)
            render(im).save(os.path.join(OUT, fn), "JPEG", quality=84, optimize=True)
            cands.append(dict(series=name, file=fn, pid=p["id"], site=p["site"],
                              score=p["score"], w=p["w"], h=p["h"], url=p["url"],
                              tags=p["tags"][:600]))
            n += 1
        except Exception as e:
            print("   dl err", p.get("id"), type(e).__name__, flush=True)
        time.sleep(0.2)
    print("   previews=%d" % n, flush=True)

json.dump(cands, open("_tmp/lowrun22/cands.json", "w"), indent=1)
print("TOTAL candidates", len(cands), flush=True)
