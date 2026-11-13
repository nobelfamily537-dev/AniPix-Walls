#!/usr/bin/env python3
"""Reframe picks whose art sits inside a larger dark canvas (blur-fill)."""
import json, io, os, subprocess, time
import numpy as np
import requests
from PIL import Image, ImageFilter, ImageEnhance

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
cfg = json.load(open("_tmp/lc4/rerender.json"))
wp = json.load(open("wallpapers.json"))
ents = {}
for cat, items in wp["categories"].items():
    for e in items:
        ents[e["id"]] = (cat, e)


def fetch(key):
    if key.startswith("wh"):
        wid = key[2:]
        for ext in ("jpg", "png"):
            u = f"https://w.wallhaven.cc/full/{wid[:2]}/wallhaven-{wid}.{ext}"
            try:
                r = requests.get(u, headers=UA, timeout=60)
                if r.status_code == 200 and len(r.content) > 20000:
                    return r.content
            except Exception:
                pass
        return None
    if key.startswith("sb"):
        sid = key[2:]
        try:
            r = requests.get("https://safebooru.org/index.php", params={
                "page": "dapi", "s": "post", "q": "index", "json": "1", "id": sid, "limit": "1"},
                headers=UA, timeout=60)
            data = r.json()
            if data:
                r2 = requests.get(data[0]["file_url"], headers=UA, timeout=60)
                if r2.status_code == 200:
                    return r2.content
        except Exception:
            pass
    return None


def reframe(im):
    im = im.convert("RGB")
    g = np.asarray(im.convert("L").resize((135, 240)), dtype=np.float32)
    mask = g > 20
    if mask.mean() < 0.02:
        return None
    ys = np.where(mask.any(axis=1))[0]
    xs = np.where(mask.any(axis=0))[0]
    y0, y1 = ys[0] / 240, (ys[-1] + 1) / 240
    x0, x1 = xs[0] / 135, (xs[-1] + 1) / 135
    if (y1 - y0) > 0.82 and (x1 - x0) > 0.82:
        return None                      # art already fills the frame
    W, H = im.size
    box = (int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H))
    box = (max(0, box[0] - 8), max(0, box[1] - 8), min(W, box[2] + 8), min(H, box[3] + 8))
    cut = im.crop(box)
    if cut.width < 400 or cut.height < 400:
        return None
    bg = cut.copy()
    s = max(1080 / bg.width, 1920 / bg.height)
    bg = bg.resize((max(1080, int(bg.width * s) + 1), max(1920, int(bg.height * s) + 1)), Image.LANCZOS)
    x = (bg.width - 1080) // 2
    y = (bg.height - 1920) // 2
    bg = bg.crop((x, y, x + 1080, y + 1920)).filter(ImageFilter.GaussianBlur(38))
    bg = ImageEnhance.Brightness(bg).enhance(0.55)
    bg = ImageEnhance.Color(bg).enhance(0.9)
    s2 = min(1080 / cut.width, (1920 * 0.98) / cut.height)
    fg = cut.resize((max(1, int(cut.width * s2)), max(1, int(cut.height * s2))), Image.LANCZOS)
    canvas = bg.copy()
    canvas.paste(fg, ((1080 - fg.width) // 2, (1920 - fg.height) // 2))
    return canvas


done = skipped = 0
for it in cfg["items"]:
    i, cat, key = it["id"], it["cat"], it["key"]
    if i not in ents:
        continue
    raw = fetch(key)
    if not raw:
        print("no source", i, key)
        continue
    try:
        im = Image.open(io.BytesIO(raw))
        im.load()
    except Exception:
        print("bad", i)
        continue
    out = reframe(im)
    if out is None:
        skipped += 1
        continue
    full = out.resize((1080, 1920), Image.LANCZOS)
    full.save(os.path.join(cat, i + ".jpg"), "JPEG", quality=95, optimize=True, progressive=True)
    full.resize((360, 640), Image.LANCZOS).save(
        os.path.join(cat, i + "_thumb.jpg"), "JPEG", quality=80, optimize=True, progressive=True)
    done += 1
    print("reframed", i, key)
    time.sleep(0.3)

json.dump(wp, open("wallpapers.json", "w"), ensure_ascii=False, separators=(",", ":"))
print("done", done, "skipped", skipped)
for p in ("_tmp/lc4/rr2.py", "_tmp/lc4/rerender.json", "_tmp/lc4/trigger-rr2.txt",
          ".github/workflows/_tmp-lc-rr2.yml"):
    if os.path.exists(p):
        subprocess.run(["git", "rm", "-q", "-f", p], check=False)
