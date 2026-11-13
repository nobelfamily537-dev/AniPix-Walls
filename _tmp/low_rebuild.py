#!/usr/bin/env python3
"""Rebuild the low-count batch: conservative letterbox trim + 9:16 render,
re-insert any entries missing from wallpapers.json."""
import io, json, hashlib, os, subprocess, time
import numpy as np
import requests
from PIL import Image, ImageFilter, ImageOps

UA = {"User-Agent": "AniPixBot/1.0 (wallpaper curation)"}
RAW = "https://raw.githubusercontent.com/nobelfamily537-dev/AniPix-Walls/main"
NAME, MAIL = "AniPix Bot", "nobelfamily537@gmail.com"
TODAY = "2026-11-13"


def trim_bars(im):
    """Remove only near-pure uniform black/white bars (letterboxing)."""
    a = np.asarray(im.convert("L"), dtype=np.float32)
    h, w = a.shape
    rm, rs = a.mean(1), a.std(1)
    cm, cs = a.mean(0), a.std(0)

    def edges(vals, stds, n):
        t = 0
        while t < n * 0.6 and stds[t] < 2.5 and (vals[t] < 9 or vals[t] > 247):
            t += 1
        b = n
        while b > n * 0.4 and stds[b - 1] < 2.5 and (vals[b - 1] < 9 or vals[b - 1] > 247):
            b -= 1
        return t, b

    t, b = edges(rm, rs, h)
    l, r = edges(cm, cs, w)
    if (b - t) < h * 0.3 or (r - l) < w * 0.3:
        return im
    if (t, b, l, r) == (0, h, 0, w):
        return im
    print("   trimmed %dx%d -> %dx%d" % (w, h, r - l, b - t), flush=True)
    return im.crop((l, t, r, b))


def render(im):
    w, h = im.size
    ratio = h / w
    t = 9 / 16
    if ratio > 2.05 or ratio < 0.62:
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

rebuilt = restored = 0
for p in picks:
    wid = "wpx" + hashlib.sha1(p["url"].encode()).hexdigest()[:10]
    cat = p["cat"]
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
        im = trim_bars(im)
        full = render(im)
        os.makedirs(cat, exist_ok=True)
        full.save("%s/%s.jpg" % (cat, wid), "JPEG", quality=95, optimize=True, progressive=True)
        full.resize((360, 640), Image.LANCZOS).save("%s/%s_thumb.jpg" % (cat, wid), "JPEG",
                                                   quality=80, optimize=True, progressive=True)
        rebuilt += 1
    except Exception as e:
        print("ERR", p["url"], e, flush=True)
        continue

    if wid not in byid:
        tags = [x.strip().lower() for x in p["tags"].split(",") if x.strip()]
        seen = set()
        tags = [x for x in tags if not (x in seen or seen.add(x))]
        data["categories"][cat].insert(0, {
            "id": wid,
            "thumb": "%s/%s/%s_thumb.jpg" % (RAW, cat, wid),
            "full": "%s/%s/%s.jpg" % (RAW, cat, wid),
            "alt": "%s/%s/%s.jpg" % (RAW, cat, wid),
            "tags": ",".join(tags),
            "date": TODAY,
        })
        for tg in tags:
            data["tags"].setdefault(tg, [])
            if wid not in data["tags"][tg]:
                data["tags"][tg].insert(0, wid)
        byid[wid] = (cat, None)
        restored += 1
        print("RESTORED", p["series"], wid, flush=True)
    time.sleep(0.1)

data["version"] = int(data.get("version", 1)) + 1
data["last_updated"] = TODAY
json.dump(data, open("wallpapers.json", "w", encoding="utf-8"), ensure_ascii=False,
          separators=(",", ":"))
print("\nrebuilt %d restored %d" % (rebuilt, restored))
subprocess.run(["git", "add", "-A"], check=True)
msg = "Wallpaper top-up - %s (%d new across 8 series)" % (TODAY, rebuilt)
subprocess.run(["git", "-c", "user.name=" + NAME, "-c", "user.email=" + MAIL, "commit", "-m", msg], check=True)
subprocess.run(["git", "push"], check=True)
print("PUSHED", msg)
