#!/usr/bin/env python3
"""Low-count run 22 - stage 1e: wallhaven search + per-wall tag verification."""
import os, io, json, time
import requests
from PIL import Image

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json"}
OUT = "_tmp/lowrun22/preview3"
os.makedirs(OUT, exist_ok=True)
picks = json.load(open(os.environ.get("PICKS", "_tmp/lowrun22/picks5.json")))
excl = set(json.load(open("_tmp/lowrun22/exclude.json")))
ALIAS = json.load(open("_tmp/lowrun22/alias.json"))
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


def get(url, params=None):
    for _ in range(3):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                print("   429 sleep", flush=True); time.sleep(20); continue
            if r.status_code == 404:
                return None
            print("   HTTP", r.status_code, url, flush=True)
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
        if len(verified) >= 14 or checks >= 22:
            break
        if it["id"] in excl:
            continue
        w, h = it["dimension_x"], it["dimension_y"]
        if h < 1700 or w < 900 or w / h > 2.0 or w / h < 0.45:
            continue
        checks += 1
        d = get("https://wallhaven.cc/api/v1/w/%s" % it["id"])
        time.sleep(1.5)
        if not d:
            continue
        tg = [t["name"].lower() for t in d.get("data", {}).get("tags", [])]
        hit = [t for t in tg if any(t == a or t.startswith(a) for a in al)]
        if not hit:
            continue
        it["tags"] = " ".join(t.replace(" ", "_") for t in tg)[:600]
        it["series_tag"] = hit[0]
        verified.append(it)
    print("   verified=%d (checked %d)" % (len(verified), checks), flush=True)

    n = 0
    for it in verified:
        try:
            r = requests.get(it["path"], headers=UA, timeout=45)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            fn = "%s_%02d.jpg" % (slug, n)
            render(im).save(os.path.join(OUT, fn), "JPEG", quality=84, optimize=True)
            cands.append(dict(series=name, file=fn, pid=it["id"], site="wh",
                              score=it.get("favorites", 0), w=it["dimension_x"], h=it["dimension_y"],
                              url=it["path"], tags=it["tags"], series_tag=it["series_tag"]))
            n += 1
        except Exception as e:
            print("   dl err", it["id"], type(e).__name__, flush=True)
        time.sleep(0.2)
    print("   previews=%d" % n, flush=True)

json.dump(cands, open("_tmp/lowrun22/cands3.json", "w"), indent=1)
print("TOTAL", len(cands), flush=True)
