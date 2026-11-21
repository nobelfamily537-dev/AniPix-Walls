#!/usr/bin/env python3
"""Regenerate and stage the 20 wallpaper image pairs whose metadata is already in wallpapers.json."""
import io, json, os, hashlib, subprocess
import requests
from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = 200_000_000
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
OUT = "_tmp/night20"

picks = json.load(open(os.path.join(OUT, "picks.json")))
cands = {}
for fn in ("cands.json", "cands3.json", "cands4.json"):
    p = os.path.join(OUT, fn)
    if os.path.exists(p):
        for c in json.load(open(p)):
            cands[str(c["pid"])] = c

data = json.load(open("wallpapers.json"))
have = {}
for cat, arr in data["categories"].items():
    for w in arr:
        have[w["id"]] = cat

def make_id(pid):
    return "wpx" + hashlib.sha1(("night20-%s" % pid).encode()).hexdigest()[:10]

def fit(im):
    return ImageOps.fit(im, (1080, 1920), method=Image.LANCZOS, centering=(0.5, 0.42))

staged, failed = [], []
for p in picks:
    pid = str(p["pid"])
    wid = make_id(pid)
    cat = p["category"]
    if wid not in have:
        failed.append((pid, "not in wallpapers.json"))
        continue
    c = cands.get(pid)
    if not c:
        failed.append((pid, "no candidate"))
        continue
    full = os.path.join(cat, wid + ".jpg")
    thumb = os.path.join(cat, wid + "_thumb.jpg")
    try:
        if not (os.path.exists(full) and os.path.exists(thumb)):
            r = requests.get(c["url"], headers=UA, timeout=90)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            final = fit(im)
            os.makedirs(cat, exist_ok=True)
            final.save(full, "JPEG", quality=95, optimize=True, subsampling=1)
            final.resize((360, 640), Image.LANCZOS).save(thumb, "JPEG", quality=80, optimize=True)
        for f in (full, thumb):
            blob = subprocess.check_output(["git", "hash-object", "-w", f]).decode().strip()
            subprocess.check_call(["git", "update-index", "--add", "--cacheinfo", "100644,%s,%s" % (blob, f)])
        staged.append((cat, wid))
        print("ok", cat, wid, os.path.getsize(full), os.path.getsize(thumb), flush=True)
    except Exception as e:
        failed.append((pid, "%s %s" % (type(e).__name__, e)))
        print("FAIL", pid, type(e).__name__, e, flush=True)

print("STAGED", len(staged), "FAILED", len(failed), flush=True)
json.dump({"staged": staged, "failed": failed}, open(os.path.join(OUT, "fixreport.json"), "w"), indent=1)
