#!/usr/bin/env python3
"""Night run process: turn chosen candidates into final 1080x1920 wallpapers."""
import os, io, json, hashlib, random
import requests
from PIL import Image, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
REPO = "nobelfamily537-dev/AniPix-Walls"
RAW = f"https://raw.githubusercontent.com/{REPO}/main"
DATE = "2026-11-21"
picks = json.load(open("_tmp/nightrun6/picks.json"))
data = json.load(open("wallpapers.json", encoding="utf-8"))

existing_ids = set()
for cat, lst in data["categories"].items():
    for e in lst:
        existing_ids.add(e["id"])


def dhash(im, size=8):
    im = im.convert("L").resize((size + 1, size), Image.LANCZOS)
    px = list(im.getdata())
    bits = []
    for row in range(size):
        for col in range(size):
            bits.append(px[row * (size + 1) + col] < px[row * (size + 1) + col + 1])
    return bits


def ham(a, b):
    return sum(1 for x, y in zip(a, b) if x != y)


print("building dhash index of existing wallpapers...", flush=True)
hashes = []
for cat in ("anime", "anime2", "game", "nature", "god", "live", "space", "ai3d"):
    d = cat
    if not os.path.isdir(d):
        continue
    for fn in os.listdir(d):
        if fn.endswith("_thumb.jpg") or not fn.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        try:
            hashes.append(dhash(Image.open(os.path.join(d, fn))))
        except Exception:
            pass
print("existing hashes:", len(hashes), flush=True)


def render(im, size=(1080, 1920)):
    w, h = im.size
    r = h / w
    t = 16 / 9
    if r > 2.2:
        bg = ImageOps.fit(im, size, method=Image.LANCZOS).filter(ImageFilter.GaussianBlur(22))
        fg = im.copy()
        fg.thumbnail(size, Image.LANCZOS)
        bg.paste(fg, ((size[0] - fg.width) // 2, (size[1] - fg.height) // 2))
        return bg
    if r > t:
        nh = int(w * t)
        y = int((h - nh) * 0.05)
        return im.crop((0, y, w, y + nh))
    nw = int(h / t)
    x = (w - nw) // 2
    return im.crop((x, 0, x + nw, h))


added = []
for p in picks:
    cat = p["cat"]
    try:
        r = requests.get(p["url"], headers=UA, timeout=60)
        r.raise_for_status()
        im = Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception as e:
        print("dl fail", p.get("pid"), type(e).__name__, flush=True)
        continue
    hb = dhash(im)
    if any(ham(hb, x) <= 6 for x in hashes):
        print("dup-art skip", p.get("pid"), flush=True)
        continue
    out = render(im).resize((1080, 1920), Image.LANCZOS)
    wid = "wpx" + hashlib.md5((str(p["pid"]) + p["url"] + DATE).encode()).hexdigest()[:10]
    if wid in existing_ids:
        print("id collision", wid, flush=True)
        continue
    os.makedirs(cat, exist_ok=True)
    out.save(f"{cat}/{wid}.jpg", "JPEG", quality=95, optimize=True)
    t = out.copy()
    t.thumbnail((360, 640), Image.LANCZOS)
    t.save(f"{cat}/{wid}_thumb.jpg", "JPEG", quality=80, optimize=True)
    entry = {
        "id": wid,
        "thumb": f"{RAW}/{cat}/{wid}_thumb.jpg",
        "full": f"{RAW}/{cat}/{wid}.jpg",
        "alt": f"{RAW}/{cat}/{wid}.jpg",
        "tags": p["tags"].strip().lower(),
        "date": DATE,
    }
    data["categories"][cat].append(entry)
    existing_ids.add(wid)
    hashes.append(hb)
    added.append((cat, wid, p["series"]))
    print("added", cat, wid, p["series"], flush=True)

if added:
    data["version"] = int(data.get("version", 0)) + 1
    data["last_updated"] = DATE
    # refresh tag index
    idx = {}
    for cat, lst in data["categories"].items():
        for e in lst:
            for tg in e.get("tags", "").split(","):
                tg = tg.strip().lower()
                if tg:
                    idx.setdefault(tg, []).append(e["id"])
    data["tags"] = idx
    json.dump(data, open("wallpapers.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)

json.dump(added, open("_tmp/nightrun6/added.json", "w"), indent=1)
print("TOTAL added", len(added), flush=True)
