#!/usr/bin/env python3
"""Re-render today's low-count picks with robust uniform-border trimming.
Drops entries whose trimmed art is too wide for a good 9:16 crop."""
import io, json, hashlib, os, subprocess, time
import numpy as np
import requests
from PIL import Image, ImageFilter, ImageOps

UA = {"User-Agent": "AniPixBot/1.0 (wallpaper curation)"}
NAME, MAIL = "AniPix Bot", "nobelfamily537@gmail.com"
TODAY = "2026-11-13"


def band(vals, stds, minfrac=0.28, maxfrac=0.72):
    n = len(vals)
    t = 0
    while t < n * maxfrac and stds[t] < 6 and (vals[t] < 14 or vals[t] > 241):
        t += 1
    b = n
    while b > n * (1 - maxfrac) and stds[b - 1] < 6 and (vals[b - 1] < 14 or vals[b - 1] > 241):
        b -= 1
    return t, b


def content_box(im):
    a = np.asarray(im.convert("L"), dtype=np.float32)
    h, w = a.shape
    t, b = band(a.mean(1), a.std(1))
    l, r = band(a.mean(0), a.std(0))
    if (b - t) > h * 0.3 and (r - l) > w * 0.3 and (t, b, l, r) != (0, h, 0, w):
        return im.crop((l, t, r, b))
    return im


def render(im):
    w, h = im.size
    ratio = h / w
    t = 9 / 16
    if ratio > 2.05:
        bg = ImageOps.fit(im, (1080, 1920), method=Image.LANCZOS).filter(ImageFilter.GaussianBlur(30))
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

fixed = dropped = 0
for p in picks:
    wid = "wpx" + hashlib.sha1(p["url"].encode()).hexdigest()[:10]
    if wid not in byid:
        print("not in json", wid)
        continue
    cat, entry = byid[wid]
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
        im = content_box(im)
        w, h = im.size
        if w / h > 1.45:
            # too wide to crop to 9:16 without ruining it -> drop entry
            data["categories"][cat] = [e for e in data["categories"][cat] if e["id"] != wid]
            for tg, ids in data["tags"].items():
                if wid in ids:
                    data["tags"][tg] = [x for x in ids if x != wid]
            for f in ("%s/%s.jpg" % (cat, wid), "%s/%s_thumb.jpg" % (cat, wid)):
                if os.path.exists(f):
                    os.remove(f)
            dropped += 1
            print("DROPPED", p["series"], wid, "aspect %.2f" % (w / h), flush=True)
            continue
        full = render(im)
        full.save("%s/%s.jpg" % (cat, wid), "JPEG", quality=95, optimize=True, progressive=True)
        full.resize((360, 640), Image.LANCZOS).save("%s/%s_thumb.jpg" % (cat, wid), "JPEG",
                                                   quality=80, optimize=True, progressive=True)
        fixed += 1
        print("FIXED", p["series"], wid, "%dx%d" % (w, h), flush=True)
    except Exception as e:
        print("ERR", p["url"], e, flush=True)
    time.sleep(0.1)

# drop empty tag keys
for tg in [k for k, v in data["tags"].items() if not v]:
    del data["tags"][tg]

json.dump(data, open("wallpapers.json", "w", encoding="utf-8"), ensure_ascii=False,
          separators=(",", ":"))
print("\nFIXED %d DROPPED %d" % (fixed, dropped))
subprocess.run(["git", "add", "-A"], check=True)
msg = "Wallpaper top-up - %s (crop fixes, %d refreshed, %d dropped)" % (TODAY, fixed, dropped)
subprocess.run(["git", "-c", "user.name=" + NAME, "-c", "user.email=" + MAIL, "commit", "-m", msg], check=True)
subprocess.run(["git", "push"], check=True)
print("PUSHED", msg)
