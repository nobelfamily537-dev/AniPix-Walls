#!/usr/bin/env python3
"""Trim empty (black) borders from the new batch and blur-fill to 1080x1920."""
import json, os, subprocess
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance

wp = json.load(open("wallpapers.json"))
items = [(c, e) for c, v in wp["categories"].items() for e in v if e.get("date") == "2026-11-13"]
done = 0
for cat, e in items:
    p = os.path.join(cat, e["id"] + ".jpg")
    if not os.path.exists(p):
        continue
    im = Image.open(p).convert("RGB")
    g = np.asarray(im.convert("L"), dtype=np.float32)
    rows = g.mean(axis=1) > 10
    cols = g.mean(axis=0) > 10
    if rows.sum() < 10 or cols.sum() < 10:
        continue
    ys = np.where(rows)[0]
    xs = np.where(cols)[0]
    y0, y1 = int(ys[0]), int(ys[-1]) + 1
    x0, x1 = int(xs[0]), int(xs[-1]) + 1
    if (y1 - y0) > 0.94 * im.height and (x1 - x0) > 0.94 * im.width:
        continue
    cut = im.crop((x0, y0, x1, y1))
    if cut.width < 300 or cut.height < 300:
        continue
    bg = cut.copy()
    s = max(1080 / bg.width, 1920 / bg.height)
    bg = bg.resize((max(1080, int(bg.width * s) + 1), max(1920, int(bg.height * s) + 1)), Image.LANCZOS)
    bx = (bg.width - 1080) // 2
    by = (bg.height - 1920) // 2
    bg = bg.crop((bx, by, bx + 1080, by + 1920)).filter(ImageFilter.GaussianBlur(40))
    bg = ImageEnhance.Brightness(bg).enhance(0.55)
    bg = ImageEnhance.Color(bg).enhance(0.9)
    s2 = min(1080 / cut.width, (1920 * 0.99) / cut.height)
    fg = cut.resize((max(1, int(cut.width * s2)), max(1, int(cut.height * s2))), Image.LANCZOS)
    canvas = bg.copy()
    canvas.paste(fg, ((1080 - fg.width) // 2, (1920 - fg.height) // 2))
    canvas.save(p, "JPEG", quality=95, optimize=True, progressive=True)
    canvas.resize((360, 640), Image.LANCZOS).save(
        os.path.join(cat, e["id"] + "_thumb.jpg"), "JPEG", quality=80, optimize=True, progressive=True)
    done += 1
    print("fixed", e["id"], (x0, y0, x1, y1))
print("done", done, "of", len(items))
for f in ("_tmp/lc8/fixband.py", "_tmp/lc8/trigger.txt", ".github/workflows/_tmp-lc-fb.yml"):
    if os.path.exists(f):
        subprocess.run(["git", "rm", "-q", "-f", f], check=False)
