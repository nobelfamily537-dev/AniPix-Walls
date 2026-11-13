#!/usr/bin/env python3
"""Repair pass: strip transparent-canvas black bands, replace the 4 unusable picks."""
import os, io, json, hashlib
import urllib.request
import numpy as np
from PIL import Image

DATE = "2026-11-13"
BASE = "https://raw.githubusercontent.com/nobelfamily537-dev/AniPix-Walls/main"
W, H = 1080, 1920
REMOVE = ["wpx8207206f7a", "wpx5a45788db9", "wpxb11d2ce69b", "wpxe27bdf62f9"]
ADD = [
    (101, "anime2", "innocent zero,mashle,mashle magic and muscles,blonde hair,villain,dark magic,green glow,crown,dramatic,dark background,fantasy,anime boy,powerful,menacing,anime wallpaper"),
    (144, "anime", "riko,reg,made in abyss,night,stars,cliff,monster,adventure,glowing,dark,scenery,anime landscape,moody,wonder,anime wallpaper"),
]
UA = {"User-Agent": "AniPixBot/1.0 (wallpaper curator)"}


def content_bbox(im):
    g = np.asarray(im.convert("RGB")).max(axis=2)
    m = g > 15
    r = np.where(m.mean(axis=1) > 0.05)[0]
    c = np.where(m.mean(axis=0) > 0.05)[0]
    if not len(r) or not len(c):
        return (0, 0, im.width, im.height)
    return (int(c.min()), int(r.min()), int(c.max()) + 1, int(r.max()) + 1)


def cover(art):
    s = max(W / art.width, H / art.height)
    r = art.resize((max(W, int(art.width * s + 0.5)), max(H, int(art.height * s + 0.5))), Image.LANCZOS)
    x = (r.width - W) // 2
    y = (r.height - H) // 2
    return r.crop((x, y, x + W, y + H))


def flatten(im):
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        flat = Image.new("RGB", im.size, (255, 255, 255))
        flat.paste(im, mask=im.split()[-1])
        return flat
    return im.convert("RGB")


wp = json.load(open("wallpapers.json"))
removed = set()
for cat, lst in wp["categories"].items():
    keep = []
    for e in lst:
        if e["id"] in REMOVE:
            for p in (f"{cat}/{e['id']}.jpg", f"{cat}/{e['id']}_thumb.jpg"):
                if os.path.exists(p):
                    os.remove(p)
            removed.add(e["id"])
            print("removed", cat, e["id"], flush=True)
        else:
            keep.append(e)
    wp["categories"][cat] = keep

added = json.load(open("_tmp/n2/added.json"))
final = []
for cat, iid, slug, src, cid in added:
    if iid in removed:
        continue
    p = f"{cat}/{iid}.jpg"
    if not os.path.exists(p):
        continue
    im = Image.open(p).convert("RGB")
    b = content_bbox(im)
    if b != (0, 0, im.width, im.height):
        out = cover(im.crop(b))
        out.save(p, "JPEG", quality=95, optimize=True)
        out.resize((360, 640), Image.LANCZOS).save(f"{cat}/{iid}_thumb.jpg", "JPEG", quality=80, optimize=True)
        print("repaired", iid, b, flush=True)
    final.append([cat, iid, slug, src, cid])

cands = {c["idx"]: c for c in json.load(open("_tmp/n2/cands.json"))}
have = {e["id"] for c in wp["categories"].values() for e in c}
for idx, cat, tags in ADD:
    c = cands[idx]
    iid = "wpx" + hashlib.md5((c["slug"] + "|" + c["cid"]).encode()).hexdigest()[:10]
    if iid in have:
        print("dup", iid, flush=True)
        continue
    req = urllib.request.Request(c["url"], headers=UA)
    im = flatten(Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=180).read())))
    b = content_bbox(im)
    art = im.crop(b)
    out = cover(art)
    os.makedirs(cat, exist_ok=True)
    out.save(f"{cat}/{iid}.jpg", "JPEG", quality=95, optimize=True)
    out.resize((360, 640), Image.LANCZOS).save(f"{cat}/{iid}_thumb.jpg", "JPEG", quality=80, optimize=True)
    full = f"{BASE}/{cat}/{iid}.jpg"
    wp["categories"][cat].insert(0, {"id": iid, "thumb": f"{BASE}/{cat}/{iid}_thumb.jpg",
                                     "full": full, "alt": full, "tags": tags, "date": DATE})
    have.add(iid)
    final.append([cat, iid, c["slug"], c["src"], c["cid"]])
    print("added", cat, iid, c["slug"], flush=True)

wp["version"] = int(wp.get("version", 0)) + 1
wp["last_updated"] = DATE
with open("wallpapers.json", "w", encoding="utf-8") as f:
    json.dump(wp, f, ensure_ascii=False, separators=(",", ":"))
json.dump(final, open("_tmp/n2/added.json", "w"), indent=1)
print("FINAL", len(final), "version", wp["version"], flush=True)
