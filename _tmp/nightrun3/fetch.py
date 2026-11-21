#!/usr/bin/env python3
"""Lean night fetch: wallhaven series-level only, one page each."""
import os, io, json, time, re
import requests
from PIL import Image, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
QUERIES = [("dorohedoro","caiman"),("dorohedoro","nikaido"),("dorohedoro","noi dorohedoro"),("hellsing","alucard"),("hellsing","seras victoria"),("hellsing","integrity hellsing"),("tower of god","bam tower of god"),("tower of god","khun aguero"),("samurai champloo","mugen samurai champloo"),("samurai champloo","jin samurai champloo"),("samurai champloo","fuu samurai champloo"),("mushishi","ginko mushishi"),("nichijou","nano shinonome"),("nichijou","aioi yuuko"),("gachiakuta","gachiakuta"),("akira","kaneda shotaro"),("slam dunk","hanamichi sakuragi"),("yu yu hakusho","hiei yu yu hakusho")]
          "yu yu hakusho", "gachiakuta", "mushishi", "nichijou", "slam dunk",
          "akira anime", "death parade", "shangri la frontier", "undead unluck",
          "world trigger", "baki"]
BAD = {"text", "english_text", "watermark", "signature", "artist_name", "speech_bubble", "comic",
       "logo", "border", "frame", "monochrome", "greyscale", "sketch", "chibi", "photo", "cosplay",
       "screencap", "screenshot", "collage", "crossover", "vector", "lineart", "meme", "sign",
       "bikini", "swimsuit", "lingerie", "cleavage", "large_breasts", "nude", "naked", "topless"}
OUT = "_tmp/nightrun3/pv"
os.makedirs(OUT, exist_ok=True)
diag = {}


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


def get(url, params=None, timeout=40):
    try:
        t0 = time.time()
        r = requests.get(url, params=params, headers=UA, timeout=timeout)
        diag.setdefault("timings", []).append(round(time.time() - t0, 1))
        if r.status_code == 200:
            return r
        print("  HTTP", r.status_code, url, flush=True)
    except Exception as e:
        print("  ERR", type(e).__name__, str(e)[:80], flush=True)
    return None


cands, summary = [], {}
for name, q in QUERIES:
    pool = []
    for page in (1, 2):
        r = get("https://wallhaven.cc/api/v1/search",
                {"q": q, "categories": "111", "purity": "100",
                 "atleast": "900x1300", "sorting": "favorites", "order": "desc", "page": page})
        if not r:
            continue
        try:
            js = r.json()
        except Exception:
            continue
        data = js.get("data") or []
        print("  wh %s/%s p%d -> %d" % (name, q, page, len(data)), flush=True)
        for p in data:
            pool.append(dict(site="wallhaven", id=p.get("id"), score=0,
                             w=p.get("dimension_x") or 0, h=p.get("dimension_y") or 0,
                             url=p.get("path"), prev=(p.get("thumbs") or {}).get("large") or p.get("path"),
                             tags=" ".join(t.get("name", "") for t in (p.get("tags") or []))))
        time.sleep(0.4)
    reasons = {"landscape": 0, "small": 0, "bad": 0}
    seen, kept = set(), []
    for p in pool:
        if p["id"] in seen:
            continue
        seen.add(p["id"])
        w, h = p["w"], p["h"]
        if not w or not h or not p.get("url"):
            continue
        if h / w < 1.15:
            reasons["landscape"] += 1
            continue
        if h < 1400 or w < 750:
            reasons["small"] += 1
            continue
        if set(p["tags"].split()) & BAD:
            reasons["bad"] += 1
            continue
        kept.append(p)
    slug = re.sub(r"[^a-z0-9]+", "-", name + "-" + q).strip("-")
    summary[slug] = dict(pool=len(pool), valid=len(kept), reasons=reasons)
    print("== %s pool=%d valid=%d %s" % (slug, len(pool), len(kept), reasons), flush=True)
    n = 0
    for p in kept:
        if n >= 6:
            break
        try:
            r = requests.get(p["prev"], headers=UA, timeout=45)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            fn = "%s_%02d.jpg" % (slug, n)
            render(im).save(os.path.join(OUT, fn), "JPEG", quality=82, optimize=True)
            cands.append(dict(series=name, slug=slug, file=fn, pid=p["id"], site=p["site"],
                              w=p["w"], h=p["h"], url=p["url"], tags=p["tags"][:500]))
            n += 1
        except Exception as e:
            print("   dl err", p.get("id"), type(e).__name__, flush=True)
    print("   previews=%d" % n, flush=True)

json.dump(dict(cands=cands, summary=summary, diag=diag), open("_tmp/nightrun3/candidates.json", "w"), indent=1)
print("TOTAL", len(cands), flush=True)
