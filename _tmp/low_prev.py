#!/usr/bin/env python3
"""Render full-art previews (contain, blurred fill) for the low-count candidate list."""
import io, json, os, time
import requests
from PIL import Image, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
OUT = "_tmp/prev_low"
os.makedirs(OUT, exist_ok=True)
cands = json.load(open("_tmp/cand_all.json"))
W, H = 400, 711
out = []
for c in cands:
    try:
        r = requests.get(c["url"], headers=UA, timeout=60)
        r.raise_for_status()
        im = Image.open(io.BytesIO(r.content))
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            bbox = im.getbbox()
            if bbox: im = im.crop(bbox)
            flat = Image.new("RGB", im.size, (255, 255, 255))
            flat.paste(im, mask=im.split()[-1])
            im = flat
        im = im.convert("RGB")
        bg = ImageOps.fit(im, (W, H), method=Image.LANCZOS).filter(ImageFilter.GaussianBlur(18))
        fg = im.copy()
        fg.thumbnail((W, H), Image.LANCZOS)
        bg.paste(fg, ((W - fg.width) // 2, (H - fg.height) // 2))
        bg.save(f"{OUT}/{c['file']}", "JPEG", quality=86, optimize=True)
        c["full_w"], c["full_h"] = im.size
        out.append(c)
        print("ok", c["file"], im.size, flush=True)
    except Exception as e:
        print("err", c["file"], str(e)[:90], flush=True)
    time.sleep(0.05)
json.dump(out, open("_tmp/cand_all.json", "w"), indent=1)
print("TOTAL", len(out), flush=True)
