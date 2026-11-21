#!/usr/bin/env python3
"""Final pass: find the art band by row/col variance and crop letterboxed canvases."""
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
    rs = a.std(1)
    cs = a.std(0)
    rows = np.where(rs > 6)[0]
    cols = np.where(cs > 6)[0]
    if len(rows) < 10 or len(cols) < 10:
        return im
    t, b = int(rows[0]), int(rows[-1]) + 1
    l, r = int(cols[0]), int(cols[-1]) + 1
    # only act when a big, dark/bright margin is removed
    top_m = a[:t].mean() if t > 0 else 0
    bot_m = a[b:].mean() if b < h else 0
    left_m = a[:, :l].mean() if l > 0 else 0
    right_m = a[:, r:].mean() if r < w else 0
    vert = (t > h * 0.12 and top_m < 26) or (h - b > h * 0.12 and bot_m < 26)
    horiz = (l > w * 0.12 and left_m < 26) or (w - r > w * 0.12 and right_m < 26)
    if not (vert or horiz):
        return im
    if (b - t) < h * 0.3 or (r - l) < w * 0.3:
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


picks = json.load(open("_tmp/pickslow.json"))
data = json.load(open("wallpapers.json", encoding="utf-8"))
byid = {}
for cat, items in data["categories"].items():
    for e in items:
        byid[e["id"]] = (cat, e)

rebuilt = 0
for p in picks:
    wid = "wpx" + hashlib.sha1(p["url"].encode()).hexdigest()[:10]
    if wid not in byid:
        continue
    cat = byid[wid][0]
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
        full.save("%s/%s.jpg" % (cat, wid), "JPEG", quality=95, optimize=True, progressive=True)
        full.resize((360, 640), Image.LANCZOS).save("%s/%s_thumb.jpg" % (cat, wid), "JPEG",
                                                   quality=80, optimize=True, progressive=True)
        rebuilt += 1
    except Exception as e:
        print("ERR", p["url"], e, flush=True)
    time.sleep(0.1)

print("rebuilt", rebuilt)
subprocess.run(["git", "add", "-A"], check=True)
msg = "Wallpaper top-up - %s (%d new across 8 series)" % (TODAY, rebuilt)
subprocess.run(["git", "-c", "user.name=" + NAME, "-c", "user.email=" + MAIL, "commit", "-m", msg], check=True)
subprocess.run(["git", "push"], check=True)
print("PUSHED", msg)
