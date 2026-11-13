#!/usr/bin/env python3
"""Fill empty top/bottom bands of the new batch with a smooth edge extension."""
import json, os, subprocess
import numpy as np
from PIL import Image, ImageFilter

wp = json.load(open("wallpapers.json"))
items = [(c, e) for c, v in wp["categories"].items() for e in v if e.get("date") == "2026-11-13"]
done = 0
for cat, e in items:
    p = os.path.join(cat, e["id"] + ".jpg")
    if not os.path.exists(p):
        continue
    im = Image.open(p).convert("RGB")
    g = np.asarray(im.convert("L"), dtype=np.float32)
    rows = g.mean(axis=1) > 12
    cols = g.mean(axis=0) > 12
    if rows.sum() < 10 or cols.sum() < 10:
        continue
    ys = np.where(rows)[0]
    xs = np.where(cols)[0]
    y0, y1 = int(ys[0]), int(ys[-1]) + 1
    x0, x1 = int(xs[0]), int(xs[-1]) + 1
    if (y1 - y0) > 0.97 * im.height and (x1 - x0) > 0.97 * im.width:
        continue
    cut = im.crop((x0, y0, x1, y1))
    if cut.width < 400 or cut.height < 200:
        continue
    # scale to full width
    if cut.width != 1080:
        s = 1080.0 / cut.width
        cut = cut.resize((1080, max(1, int(round(cut.height * s)))), Image.LANCZOS)
    if cut.height >= 1920:
        top = (cut.height - 1920) // 2
        cut = cut.crop((0, top, 1080, top + 1920))
    else:
        pad = 1920 - cut.height
        pt = pad // 2
        pb = pad - pt
        arr = np.asarray(cut)
        top_rows = np.repeat(arr[:1, :, :], pt, axis=0) if pt else None
        bot_rows = np.repeat(arr[-1:, :, :], pb, axis=0) if pb else None
        parts = [x for x in (top_rows, arr, bot_rows) if x is not None]
        canvas = np.concatenate(parts, axis=0)
        cut = Image.fromarray(canvas.astype(np.uint8))
        # soften the seams only
        blur = cut.filter(ImageFilter.GaussianBlur(18))
        mask = Image.new("L", (1080, 1920), 0)
        m = np.zeros((1920, 1080), dtype=np.uint8)
        if pt:
            m[:max(0, pt - 6), :] = 255
        if pb:
            m[1920 - max(0, pb - 6):, :] = 255
        mask = Image.fromarray(m).filter(ImageFilter.GaussianBlur(6))
        cut = Image.composite(blur, cut, mask)
    cut.save(p, "JPEG", quality=95, optimize=True, progressive=True)
    cut.resize((360, 640), Image.LANCZOS).save(
        os.path.join(cat, e["id"] + "_thumb.jpg"), "JPEG", quality=80, optimize=True, progressive=True)
    done += 1
    print("extended", e["id"], (x0, y0, x1, y1))
print("done", done, "of", len(items))
for f in ("_tmp/lcA/ext.py", "_tmp/lcA/trigger.txt", ".github/workflows/_tmp-lc-ext.yml"):
    if os.path.exists(f):
        subprocess.run(["git", "rm", "-q", "-f", f], check=False)
