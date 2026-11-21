#!/usr/bin/env python3
"""Final pass: p99-based art-band detection, render, self-validate, drop broken ones."""
import io, json, hashlib, os, subprocess, time
import numpy as np
import requests
from PIL import Image, ImageFilter, ImageOps

UA = {"User-Agent": "AniPixBot/1.0 (wallpaper curation)"}
RAW = "https://raw.githubusercontent.com/nobelfamily537-dev/AniPix-Walls/main"
NAME, MAIL = "AniPix Bot", "nobelfamily537@gmail.com"
TODAY = "2026-11-13"


def art_box(im):
    a = np.asarray(im.convert("L"), dtype=np.float32)
    h, w = a.shape
    pr = np.percentile(a, 99, axis=1)
    pc = np.percentile(a, 99, axis=0)
    rows = np.where(pr > 45)[0]
    cols = np.where(pc > 45)[0]
    if len(rows) < 10 or len(cols) < 10:
        return im
    t, b = int(rows[0]), int(rows[-1]) + 1
    l, r = int(cols[0]), int(cols[-1]) + 1
    if (b - t) < h * 0.28 or (r - l) < w * 0.28:
        return im
    if (t, b, l, r) == (0, h, 0, w):
        return im
    print("   artbox %dx%d -> %dx%d" % (w, h, r - l, b - t), flush=True)
    return im.crop((l, t, r, b))


def render(im):
    w, h = im.size
    ratio = h / w
    t = 9 / 16
    if ratio > 2.2:
        bg = ImageOps.fit(im, (1080, 1920), method=Image.LANCZOS).filter(ImageFilter.GaussianBlur(34))
        fg = im.copy()
        fg.thumbnail((1080, 1920), Image.LANCZOS)
        bg.paste(fg, ((1080 - fg.width) // 2, (1920 - fg.height) // 2))
        return bg
    if ratio > t:
        nh = int(w / t)
        y = int((h - nh) * (0.04 if ratio >= 1.55 else 0.18))
        im = im.crop((0, y, w, y + nh))
    else:
        nw = int(h * t)
        x = (w - nw) // 2
        im = im.crop((x, 0, x + nw, h))
    return ImageOps.fit(im, (1080, 1920), method=Image.LANCZOS)


def is_clean(im):
    a = np.asarray(im.convert("L"), dtype=np.float32)
    h, w = a.shape
    pr = np.percentile(a, 99, axis=1)
    pc = np.percentile(a, 99, axis=0)
    bad_r = float((pr < 32).sum()) / h
    bad_c = float((pc < 32).sum()) / w
    return max(bad_r, bad_c) <= 0.12


picks = json.load(open("_tmp/pickslow.json"))
data = json.load(open("wallpapers.json", encoding="utf-8"))
byid = {}
for cat, items in data["categories"].items():
    for e in items:
        byid[e["id"]] = (cat, e)

kept = dropped = 0
for p in picks:
    wid = "wpx" + hashlib.sha1(p["url"].encode()).hexdigest()[:10]
    if wid not in byid:
        continue
    cat = byid[wid][0]
    ok = False
    try:
        r = requests.get(p["url"], headers=UA, timeout=180)
        r.raise_for_status()
        src = Image.open(io.BytesIO(r.content))
        if src.mode in ("RGBA", "LA", "P"):
            src = src.convert("RGBA")
            bb = src.getbbox()
            if bb:
                src = src.crop(bb)
            flat = Image.new("RGB", src.size, (255, 255, 255))
            flat.paste(src, mask=src.split()[-1])
            im = flat
        else:
            im = src.convert("RGB")
        im = art_box(im)
        full = render(im)
        if not is_clean(full):
            print("BAD", p["series"], wid, flush=True)
        else:
            full.save("%s/%s.jpg" % (cat, wid), "JPEG", quality=95, optimize=True, progressive=True)
            full.resize((360, 640), Image.LANCZOS).save("%s/%s_thumb.jpg" % (cat, wid), "JPEG",
                                                       quality=80, optimize=True, progressive=True)
            kept += 1
            ok = True
    except Exception as e:
        print("ERR", p["url"], e, flush=True)
    if not ok:
        data["categories"][cat] = [e for e in data["categories"][cat] if e["id"] != wid]
        for tg, ids in list(data["tags"].items()):
            if wid in ids:
                data["tags"][tg] = [x for x in ids if x != wid]
        for f in ("%s/%s.jpg" % (cat, wid), "%s/%s_thumb.jpg" % (cat, wid)):
            if os.path.exists(f):
                os.remove(f)
        dropped += 1
    time.sleep(0.1)

for tg in [k for k, v in data["tags"].items() if not v]:
    del data["tags"][tg]

data["version"] = int(data.get("version", 1)) + 1
data["last_updated"] = TODAY
json.dump(data, open("wallpapers.json", "w", encoding="utf-8"), ensure_ascii=False,
          separators=(",", ":"))
print("\nkept %d dropped %d" % (kept, dropped))
subprocess.run(["git", "add", "-A"], check=True)
msg = "Wallpaper top-up - %s (%d new across 8 series)" % (TODAY, kept)
subprocess.run(["git", "-c", "user.name=" + NAME, "-c", "user.email=" + MAIL, "commit", "-m", msg], check=True)
subprocess.run(["git", "push"], check=True)
print("PUSHED", msg)
