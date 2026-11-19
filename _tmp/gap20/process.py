#!/usr/bin/env python3
"""Stage 2: download picked candidates, crop to 9:16, write files + wallpapers.json, commit."""
import hashlib, io, json, os, sys
import requests
from PIL import Image

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
      "Referer": "https://safebooru.org/"}
OUT = "_tmp/gap20"
TODAY = "2026-11-19"
BASE = "https://raw.githubusercontent.com/nobelfamily537-dev/AniPix-Walls/main"

picks = json.load(open(os.path.join(OUT, "picks.json")))
cands = json.load(open(os.path.join(OUT, "cands.json")))
data = json.load(open("wallpapers.json"))

existing = set()
existing_ids = set()
for cat, arr in data["categories"].items():
    for w in arr:
        existing_ids.add(w["id"])
        for k in ("full", "thumb", "alt"):
            if w.get(k):
                existing.add(w[k])


def make_id(key):
    return "wpx" + hashlib.sha1(("gap20-%s" % key).encode()).hexdigest()[:10]


def fit916(im):
    w, h = im.size
    t = 16 / 9
    r = h / w
    if r > t:
        nh = int(w * t)
        y = int((h - nh) * 0.15)
        im = im.crop((0, y, w, y + nh))
    else:
        nw = int(h / t)
        x = (w - nw) // 2
        im = im.crop((x, 0, x + nw, h))
    return im.resize((1080, 1920), Image.LANCZOS)


added = []
for p in picks:
    series = p["series"]
    n = int(p["n"])
    c = None
    for cand in cands.get(series, []):
        if cand["n"] == n:
            c = cand
            break
    if not c:
        print("SKIP no cand", series, n, flush=True)
        continue
    cat = p["category"]
    assert cat in ("anime", "anime2"), cat
    wid = make_id(c["hash"])
    if wid in existing_ids:
        print("SKIP dup id", wid, flush=True)
        continue
    full_url = "%s/%s/%s.jpg" % (BASE, cat, wid)
    thumb_url = "%s/%s/%s_thumb.jpg" % (BASE, cat, wid)
    if full_url in existing:
        print("SKIP dup url", wid, flush=True)
        continue
    try:
        r = requests.get(c["url"], headers=UA, timeout=90)
        r.raise_for_status()
        im = Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception as e:
        print("SKIP dl", series, n, type(e).__name__, flush=True)
        continue
    final = fit916(im)
    os.makedirs(cat, exist_ok=True)
    final.save(os.path.join(cat, wid + ".jpg"), "JPEG", quality=95, optimize=True, subsampling=1)
    final.resize((360, 640), Image.LANCZOS).save(os.path.join(cat, wid + "_thumb.jpg"), "JPEG", quality=80, optimize=True)
    tags = p["tags"]
    entry = {"id": wid, "thumb": thumb_url, "full": full_url, "alt": full_url,
             "tags": tags, "date": TODAY}
    data["categories"][cat].append(entry)
    for t in [x.strip().lower() for x in tags.split(",") if x.strip()]:
        lst = data.setdefault("tags", {}).setdefault(t, [])
        if wid not in lst:
            lst.append(wid)
    existing_ids.add(wid)
    existing.add(full_url)
    added.append((cat, wid, series))
    print("ADD", cat, wid, series, n, flush=True)

if not added:
    print("NOTHING ADDED", flush=True)
    sys.exit(0)

data["version"] = int(data.get("version", 0)) + 1
data["last_updated"] = TODAY
with open("wallpapers.json", "w") as f:
    json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
print("added", len(added), "version", data["version"], flush=True)
json.dump(added, open(os.path.join(OUT, "added.json"), "w"), indent=1)
