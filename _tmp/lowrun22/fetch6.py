#!/usr/bin/env python3
"""Low-count run 22 - stage 1f: corrected 9:16 crop, portrait-first, tag-filtered."""
import os, io, json, time
import requests
from PIL import Image

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json"}
OUT = "_tmp/lowrun22/preview4"
os.makedirs(OUT, exist_ok=True)
picks = json.load(open("_tmp/lowrun22/picks6.json"))
excl = set(json.load(open("_tmp/lowrun22/exclude.json")))
ALIAS = json.load(open("_tmp/lowrun22/alias6.json"))
BADT = ("text", "english text", "quote", "typography", "logo", "watermark", "signature",
        "monochrome", "greyscale", "comic", "manga", "speech bubble", "letterboxed", "border",
        "collage", "screenshot", "photograph", "cosplay", "3d", "realistic", "vector", "sketch")
cands = []


def render(im, size=(420, 746)):
    w, h = im.size
    t = size[1] / size[0]
    nw = min(w, int(h / t))
    x = (w - nw) // 2
    im = im.crop((x, 0, x + nw, h))
    return im.resize(size, Image.LANCZOS)


def get(url, params=None):
    for _ in range(3):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                time.sleep(20); continue
            if r.status_code == 404:
                return None
            print("   HTTP", r.status_code, flush=True)
        except Exception as e:
            print("   ERR", type(e).__name__, flush=True)
        time.sleep(4)
    return None


def search(q, pages=3):
    out = []
    for page in range(1, pages + 1):
        js = get("https://wallhaven.cc/api/v1/search",
                 {"q": q, "categories": "010", "purity": "100",
                  "sorting": "favorites", "order": "desc", "page": page})
        if not js:
            break
        d = js.get("data", [])
        out += d
        if len(d) < 24:
            break
        time.sleep(1.2)
    return out


for pk in picks:
    name, slug = pk["series"], pk["slug"]
    al = [a.lower() for a in ALIAS.get(name, [name])]
    pool, seen = [], set()
    for q in pk["booru"]:
        for it in search(q):
            if it["id"] not in seen:
                seen.add(it["id"]); pool.append(it)
    print("== %s pool=%d" % (name, len(pool)), flush=True)

    verified, checks = [], 0
    for it in pool:
        if len(verified) >= 18 or checks >= 26:
            break
        if it["id"] in excl:
            continue
        w, h = it["dimension_x"], it["dimension_y"]
        if h < 1700 or w < 900 or w / h > 2.2 or w / h < 0.45:
            continue
        checks += 1
        d = get("https://wallhaven.cc/api/v1/w/%s" % it["id"])
        time.sleep(1.4)
        if not d:
            continue
        tg = [t["name"].lower() for t in d.get("data", {}).get("tags", [])]
        if not any(any(t == a or t.startswith(a) for a in al) for t in tg):
            continue
        if any(any(b in t for b in BADT) for t in tg):
            continue
        it["tags"] = " ".join(t.replace(" ", "_") for t in tg)[:600]
        verified.append(it)
    # portrait first, then by favourites
    verified.sort(key=lambda x: (0 if x["dimension_x"] / x["dimension_y"] < 1 else 1, -x.get("favorites", 0)))
    print("   verified=%d (checked %d)" % (len(verified), checks), flush=True)

    n = 0
    for it in verified:
        if n >= 16:
            break
        try:
            r = requests.get(it["path"], headers=UA, timeout=45)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            fn = "%s_%02d.jpg" % (slug, n)
            render(im).save(os.path.join(OUT, fn), "JPEG", quality=84, optimize=True)
            cands.append(dict(series=name, file=fn, pid=it["id"], site="wh",
                              score=it.get("favorites", 0), w=it["dimension_x"], h=it["dimension_y"],
                              url=it["path"], tags=it["tags"]))
            n += 1
        except Exception as e:
            print("   dl err", it["id"], type(e).__name__, flush=True)
        time.sleep(0.2)
    print("   previews=%d" % n, flush=True)

json.dump(cands, open("_tmp/lowrun22/cands4.json", "w"), indent=1)
print("TOTAL", len(cands), flush=True)
