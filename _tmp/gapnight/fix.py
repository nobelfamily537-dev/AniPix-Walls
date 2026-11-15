#!/usr/bin/env python3
"""Night gap-fill fix: remove 3 weak wallpapers, add 1 replacement."""
import io, json, os, hashlib, subprocess
import requests
from PIL import Image

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Referer": "https://konachan.net/"}
OUT = "_tmp/gapnight"
TODAY = "2026-11-15"
BASE = "https://raw.githubusercontent.com/nobelfamily537-dev/AniPix-Walls/main"

REMOVE = ["wpx1cc9783459", "wpx6944ca8742", "wpx6048c56413"]
ADD = [
    {"pid": 288274, "category": "anime2", "series": "weathering with you",
     "tags": "weathering with you,tenki no ko,amano hina,hina,floating,sky,blue sky,clouds,torii gate,shrine steps,summer,dreamy,surreal,blue theme,aesthetic"},
]

data = json.load(open("wallpapers.json"))
removed = []
for cat, arr in data["categories"].items():
    keep = []
    for w in arr:
        if w["id"] in REMOVE:
            removed.append((cat, w["id"]))
            for f in ("%s/%s.jpg" % (cat, w["id"]), "%s/%s_thumb.jpg" % (cat, w["id"])):
                if os.path.exists(f):
                    subprocess.run(["git", "rm", "-q", f], check=False)
        else:
            keep.append(w)
    data["categories"][cat] = keep
for t, ids in list(data.get("tags", {}).items()):
    new = [i for i in ids if i not in REMOVE]
    if new:
        data["tags"][t] = new
    else:
        del data["tags"][t]
print("removed", removed)

cands = {}
for fn in ("cands.json", "cands2.json", "cands3.json"):
    p = os.path.join(OUT, fn)
    if os.path.exists(p):
        for c in json.load(open(p)):
            cands[c["pid"]] = c

existing = set()
for arr in data["categories"].values():
    for w in arr:
        for k in ("full", "thumb", "alt"):
            if w.get(k):
                existing.add(w[k])


def fit916(im):
    w, h = im.size
    target = 16 / 9
    if h / w > target:
        nh = int(w * target)
        y = int((h - nh) * 0.35)
        im = im.crop((0, y, w, y + nh))
    else:
        nw = int(h * target)
        x = (w - nw) // 2
        im = im.crop((x, 0, x + nw, h))
    return im.resize((1080, 1920), Image.LANCZOS)


added = []
for p in ADD:
    c = cands[p["pid"]]
    cat = p["category"]
    wid = "wpx" + hashlib.sha1(("gapnight-%s" % p["pid"]).encode()).hexdigest()[:10]
    full_url = "%s/%s/%s.jpg" % (BASE, cat, wid)
    if full_url in existing:
        print("dup", wid); continue
    r = requests.get(c["url"], headers=UA, timeout=60)
    r.raise_for_status()
    im = Image.open(io.BytesIO(r.content)).convert("RGB")
    final = fit916(im)
    os.makedirs(cat, exist_ok=True)
    final.save(os.path.join(cat, wid + ".jpg"), "JPEG", quality=95, optimize=True, subsampling=1)
    final.resize((360, 640), Image.LANCZOS).save(os.path.join(cat, wid + "_thumb.jpg"), "JPEG", quality=80, optimize=True)
    data["categories"][cat].append({"id": wid, "thumb": full_url.replace(".jpg", "_thumb.jpg"),
                                    "full": full_url, "alt": full_url, "tags": p["tags"], "date": TODAY})
    for t in [x.strip() for x in p["tags"].split(",") if x.strip()]:
        lst = data.setdefault("tags", {}).setdefault(t, [])
        if wid not in lst:
            lst.append(wid)
    added.append(wid)

data["last_updated"] = TODAY
json.dump(data, open("wallpapers.json", "w"), ensure_ascii=False, separators=(",", ":"))
print("added", added)
