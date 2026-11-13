#!/usr/bin/env python3
"""Re-render every pick in the 2026-11-13 batch from source: trim empty borders,
cover-crop to 9:16, 1080x1920 q95 + 360x640 thumb."""
import io, json, os, subprocess, time
import numpy as np
import requests
from PIL import Image

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
TARGET = 9 / 16
cfg = json.load(open("_tmp/lc9/refetch.json"))
wp = json.load(open("wallpapers.json"))
ents = {}
for cat, v in wp["categories"].items():
    for e in v:
        ents[e["id"]] = cat


def fetch(key):
    if key.startswith("wh"):
        wid = key[2:]
        for ext in ("jpg", "png"):
            try:
                r = requests.get(f"https://w.wallhaven.cc/full/{wid[:2]}/wallhaven-{wid}.{ext}",
                                 headers=UA, timeout=120)
                if r.status_code == 200 and len(r.content) > 20000:
                    return r.content
            except Exception:
                pass
        return None
    if key.startswith("sb"):
        sid = key[2:]
        for attempt in range(2):
            try:
                r = requests.get("https://safebooru.org/index.php", params={
                    "page": "dapi", "s": "post", "q": "index", "json": "1", "id": sid, "limit": "1"},
                    headers=UA, timeout=60)
                data = r.json()
                if data:
                    r2 = requests.get(data[0]["file_url"], headers=UA, timeout=120)
                    if r2.status_code == 200 and len(r2.content) > 20000:
                        return r2.content
            except Exception:
                time.sleep(2)
        return None
    return None


def bbox(im):
    g = np.asarray(im.convert("L").resize((135, 240)), dtype=np.float32)
    b = g > 45
    rows = b.mean(axis=1) > 0.02
    cols = b.mean(axis=0) > 0.02
    if rows.sum() < 10 or cols.sum() < 10:
        return None
    ys = np.where(rows)[0]
    xs = np.where(cols)[0]
    return (max(0, int(xs[0] / 135 * im.width) - 6), max(0, int(ys[0] / 240 * im.height) - 6),
            min(im.width, int((xs[-1] + 1) / 135 * im.width) + 6),
            min(im.height, int((ys[-1] + 1) / 240 * im.height) + 6))


def cover(im):
    w, h = im.size
    if h / w > TARGET:
        nh = int(round(w / TARGET))
        y = (h - nh) // 2
        return im.crop((0, y, w, y + nh))
    nw = int(round(h * TARGET))
    x = (w - nw) // 2
    return im.crop((x, 0, x + nw, h))


ok = fail = 0
for it in cfg["items"]:
    i, cat, key = it["id"], it["cat"], it["key"]
    if i not in ents:
        continue
    raw = fetch(key)
    if not raw:
        print("no source", i, key)
        fail += 1
        continue
    try:
        im = Image.open(io.BytesIO(raw))
        im.load()
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, (16, 16, 20))
            bg.paste(im, mask=im.split()[-1])
            im = bg
        im = im.convert("RGB")
    except Exception:
        print("bad", i)
        fail += 1
        continue
    b = bbox(im)
    if b:
        cut = im.crop(b)
        if cut.width >= 500 and cut.height >= 500:
            im = cut
    out = cover(im).resize((1080, 1920), Image.LANCZOS)
    out.save(os.path.join(cat, i + ".jpg"), "JPEG", quality=95, optimize=True, progressive=True)
    out.resize((360, 640), Image.LANCZOS).save(
        os.path.join(cat, i + "_thumb.jpg"), "JPEG", quality=80, optimize=True, progressive=True)
    ok += 1
    print("rendered", i, key, im.size)
    time.sleep(0.15)

print("done", ok, "failed", fail)
json.dump(wp, open("wallpapers.json", "w"), ensure_ascii=False, separators=(",", ":"))
for f in ("_tmp/lc9/refetch.py", "_tmp/lc9/refetch.json", "_tmp/lc9/trigger.txt",
          ".github/workflows/_tmp-lc-rf.yml"):
    if os.path.exists(f):
        subprocess.run(["git", "rm", "-q", "-f", f], check=False)
