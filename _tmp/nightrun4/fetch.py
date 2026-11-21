#!/usr/bin/env python3
"""Night run 4: zerochan + gelbooru probe/fetch."""
import os, io, json, time, re
import requests
from PIL import Image, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json,text/html,*/*", "Accept-Language": "en-US,en;q=0.9"}
OUT = "_tmp/nightrun4/pv"
os.makedirs(OUT, exist_ok=True)
diag = {}
TAGS = ["Dorohedoro", "Hellsing", "Mushishi", "Samurai_Champloo", "Tower_of_God",
        "Gachiakuta", "Nichijou", "Slam_Dunk", "Beastars", "Akira"]


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


def zerochan(tag):
    out = []
    for page in (1, 2):
        try:
            r = requests.get(f"https://www.zerochan.net/{tag}", params={"json": "1", "p": page, "s": "fav"},
                             headers=UA, timeout=30)
        except Exception as e:
            diag.setdefault("zc_err", str(e)[:80]); return out
        if r.status_code != 200:
            diag.setdefault("zc_http", r.status_code); return out
        try:
            js = r.json()
        except Exception:
            diag.setdefault("zc_parse", r.text[:120]); return out
        items = js.get("items") or []
        if items:
            diag.setdefault("zc_sample", list(items[0])[:12])
        for it in items:
            out.append(dict(site="zerochan", id=it.get("id"), score=0,
                            w=it.get("width") or 0, h=it.get("height") or 0,
                            url=it.get("full"), prev=it.get("thumbnail") or it.get("full"),
                            tags=" ".join(it.get("tags") or [])))
        time.sleep(1.0)
        if len(items) < 20:
            break
    return out


def gelbooru(tag):
    out = []
    try:
        r = requests.get("https://gelbooru.com/index.php",
                         params={"page": "dapi", "s": "post", "q": "index", "json": "1",
                                 "limit": 100, "tags": tag + " sort:score:desc rating:general"},
                         headers=UA, timeout=30)
    except Exception as e:
        diag.setdefault("gb_err", str(e)[:80]); return out
    if r.status_code != 200:
        diag.setdefault("gb_http", r.status_code); return out
    try:
        js = r.json()
    except Exception:
        diag.setdefault("gb_parse", r.text[:120]); return out
    posts = js.get("post") or []
    if posts:
        diag.setdefault("gb_sample", list(posts[0])[:12])
    for p in posts:
        out.append(dict(site="gelbooru", id=p.get("id"), score=int(p.get("score") or 0),
                        w=int(p.get("width") or 0), h=int(p.get("height") or 0),
                        url=p.get("file_url"), prev=p.get("sample_url") or p.get("file_url"),
                        tags=(p.get("tags") or "")))
    return out


cands, summary = [], {}
for tag in TAGS:
    pool = zerochan(tag)
    print("  zerochan %s -> %d" % (tag, len(pool)), flush=True)
    if len(pool) < 10:
        g = gelbooru(tag.replace("_", " "))
        print("  gelbooru %s -> %d" % (tag, len(g)), flush=True)
        pool += g
    seen, kept = set(), []
    for p in pool:
        if p["id"] in seen:
            continue
        seen.add(p["id"])
        w, h = p["w"], p["h"]
        if not w or not h or not p.get("url"):
            continue
        if h / w < 1.15:
            continue
        if h < 1400 or w < 700:
            continue
        kept.append(p)
    summary[tag] = dict(pool=len(pool), valid=len(kept))
    print("== %s pool=%d valid=%d" % (tag, len(pool), len(kept)), flush=True)
    slug = tag.lower().replace("_", "-")
    n = 0
    for p in kept:
        if n >= 8:
            break
        try:
            r = requests.get(p["prev"], headers=UA, timeout=40)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            fn = "%s_%02d.jpg" % (slug, n)
            render(im).save(os.path.join(OUT, fn), "JPEG", quality=82, optimize=True)
            cands.append(dict(series=slug, file=fn, pid=p["id"], site=p["site"],
                              w=p["w"], h=p["h"], url=p["url"], tags=p["tags"][:500]))
            n += 1
        except Exception as e:
            print("   dl err", p.get("id"), type(e).__name__, str(e)[:50], flush=True)
        time.sleep(0.2)
    print("   previews=%d" % n, flush=True)

json.dump(dict(cands=cands, summary=summary, diag=diag), open("_tmp/nightrun4/candidates.json", "w"), indent=1)
print("TOTAL", len(cands), "DIAG", diag, flush=True)
