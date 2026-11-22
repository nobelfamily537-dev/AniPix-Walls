#!/usr/bin/env python3
"""Low-count run 22 - stage 1d: wallhaven only, portrait+landscape, 9:16 crop previews."""
import os, io, json, time
import requests
from PIL import Image

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json"}
OUT = "_tmp/lowrun22/preview2"
os.makedirs(OUT, exist_ok=True)
picks = json.load(open(os.environ.get("PICKS", "_tmp/lowrun22/picks3.json")))
excl = set(json.load(open("_tmp/lowrun22/exclude.json")))
cands = []


def render(im, size=(420, 746)):
    w, h = im.size
    t = size[1] / size[0]
    if h / w > t:
        nw = int(h / t); x = (w - nw) // 2
        im = im.crop((x, 0, x + nw, h))
    else:
        nh = int(w * t); y = int((h - nh) * 0.42)
        im = im.crop((0, y, w, y + nh))
    return im.resize(size, Image.LANCZOS)


def search(q, pages=3):
    out = []
    for page in range(1, pages + 1):
        try:
            r = requests.get("https://wallhaven.cc/api/v1/search",
                             params={"q": q, "categories": "010", "purity": "100",
                                     "sorting": "favorites", "order": "desc", "page": page},
                             headers=UA, timeout=30)
            if r.status_code != 200:
                print("  HTTP", r.status_code, q, flush=True); break
            js = r.json()
        except Exception as e:
            print("  ERR", type(e).__name__, q, flush=True); break
        d = js.get("data", [])
        out += d
        if len(d) < 24:
            break
        time.sleep(0.7)
    return out


for pk in picks:
    name, slug = pk["series"], pk["slug"]
    pool, seen = [], set()
    for q in pk["booru"]:
        for it in search(q):
            if it["id"] in seen:
                continue
            seen.add(it["id"])
            pool.append(it)
    kept = []
    for it in pool:
        if it["id"] in excl:
            continue
        w, h = it["dimension_x"], it["dimension_y"]
        if h < 1700 or w < 900:
            continue
        r = w / h
        if r > 2.0 or r < 0.45:
            continue
        kept.append(it)
    print("== %s pool=%d kept=%d" % (name, len(pool), len(kept)), flush=True)
    n = 0
    for it in kept:
        if n >= 16:
            break
        try:
            r = requests.get(it["path"], headers=UA, timeout=45)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            fn = "%s_%02d.jpg" % (slug, n)
            render(im).save(os.path.join(OUT, fn), "JPEG", quality=84, optimize=True)
            cands.append(dict(series=name, file=fn, pid=it["id"], site="wh", score=it.get("favorites", 0),
                              w=it["dimension_x"], h=it["dimension_y"], url=it["path"],
                              tags=" ".join(t["name"].replace(" ", "_") for t in it.get("tags", []))[:600]))
            n += 1
        except Exception as e:
            print("   dl err", it["id"], type(e).__name__, flush=True)
        time.sleep(0.15)
    print("   previews=%d" % n, flush=True)

json.dump(cands, open("_tmp/lowrun22/cands2.json", "w"), indent=1)
print("TOTAL", len(cands), flush=True)
