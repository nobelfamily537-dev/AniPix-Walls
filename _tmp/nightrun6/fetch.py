#!/usr/bin/env python3
"""Night run 6: wallhaven, allow high-res landscape for 9:16 centre crop."""
import os, io, json, time, re
import requests
from PIL import Image, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
SERIES = ["dorohedoro", "hellsing", "tower of god", "samurai champloo", "mushishi",
          "gachiakuta", "nichijou", "slam dunk", "akira", "beastars", "yu yu hakusho",
          "baki", "death parade", "undead unluck", "shangri la frontier", "world trigger"]
BAD = {"text", "english_text", "watermark", "signature", "artist_name", "speech_bubble", "comic",
       "logo", "border", "frame", "monochrome", "greyscale", "sketch", "chibi", "photo", "cosplay",
       "screencap", "screenshot", "collage", "crossover", "vector", "lineart", "meme", "sign",
       "bikini", "swimsuit", "lingerie", "cleavage", "large_breasts", "nude", "naked", "topless",
       "manga", "scan", "scan_artifacts", "real_life", "3d", "cosplayer"}
OUT = "_tmp/nightrun6/pv"
os.makedirs(OUT, exist_ok=True)


def render(im, size=(540, 960)):
    w, h = im.size
    r = h / w
    t = 16 / 9
    if r > 2.2:
        bg = ImageOps.fit(im, size, method=Image.LANCZOS).filter(ImageFilter.GaussianBlur(22))
        fg = im.copy(); fg.thumbnail(size, Image.LANCZOS)
        bg.paste(fg, ((size[0] - fg.width) // 2, (size[1] - fg.height) // 2))
        return bg
    if r > t:
        nh = int(w * t); y = int((h - nh) * 0.05)
        return im.crop((0, y, w, y + nh))
    nw = int(h / t); x = (w - nw) // 2
    return im.crop((x, 0, x + nw, h))


cands, summary = [], {}
for name in SERIES:
    pool = []
    for page in (1, 2):
        try:
            r = requests.get("https://wallhaven.cc/api/v1/search",
                             params={"q": name, "categories": "111", "purity": "100",
                                     "atleast": "1080x1920", "sorting": "favorites",
                                     "order": "desc", "page": page}, headers=UA, timeout=35)
            js = r.json()
        except Exception as e:
            print("  err", name, type(e).__name__, flush=True); continue
        data = js.get("data") or []
        print("  wh %s p%d -> %d" % (name, page, len(data)), flush=True)
        for p in data:
            pool.append(dict(id=p.get("id"), w=p.get("dimension_x") or 0, h=p.get("dimension_y") or 0,
                             url=p.get("path"), prev=(p.get("thumbs") or {}).get("large") or p.get("path"),
                             tags=" ".join(t.get("name", "") for t in (p.get("tags") or []))))
        time.sleep(0.5)
    seen, kept = set(), []
    for p in pool:
        if p["id"] in seen:
            continue
        seen.add(p["id"])
        w, h = p["w"], p["h"]
        if not w or not h or not p.get("url"):
            continue
        if h / w > 1.15:
            if w < 1080:
                continue
        else:
            if h < 1900:
                continue
        if set(p["tags"].split()) & BAD:
            continue
        kept.append(p)
    summary[name] = dict(pool=len(pool), valid=len(kept))
    print("== %s pool=%d valid=%d" % (name, len(pool), len(kept)), flush=True)
    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    n = 0
    for p in kept:
        if n >= 8:
            break
        try:
            r = requests.get(p["prev"], headers=UA, timeout=45)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            fn = "%s_%02d.jpg" % (slug, n)
            render(im).save(os.path.join(OUT, fn), "JPEG", quality=84, optimize=True)
            cands.append(dict(series=name, file=fn, pid=p["id"], w=p["w"], h=p["h"],
                              url=p["url"], tags=p["tags"][:400]))
            n += 1
        except Exception as e:
            print("   dl err", p.get("id"), type(e).__name__, flush=True)
        time.sleep(0.15)
    print("   previews=%d" % n, flush=True)

json.dump(dict(cands=cands, summary=summary), open("_tmp/nightrun6/candidates.json", "w"), indent=1)
print("TOTAL", len(cands), flush=True)
