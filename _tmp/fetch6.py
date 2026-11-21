#!/usr/bin/env python3
"""Re-render game previews from full wallhaven images with alpha/black handling."""
import os, io, json, time
import requests
from PIL import Image, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
cands = json.load(open("_tmp/candidates5.json"))
os.makedirs("_tmp/prev6", exist_ok=True)
out = []

def load(content):
    src = Image.open(io.BytesIO(content))
    if src.mode in ("RGBA", "LA", "P"):
        src = src.convert("RGBA")
        bbox = src.getbbox()
        if bbox: src = src.crop(bbox)
        flat = Image.new("RGB", src.size, (255, 255, 255))
        flat.paste(src, mask=src.split()[-1])
        return flat
    return src.convert("RGB")

def trim_borders(im, thr=24, maxfrac=0.35):
    g = im.convert("L")
    w, h = g.size
    rows = list(g.resize((1, h)).getdata())
    cols = list(g.resize((w, 1)).getdata())
    top = 0
    while top < h*maxfrac and rows[top] < thr: top += 1
    bot = h
    while bot > h*(1-maxfrac) and rows[bot-1] < thr: bot -= 1
    left = 0
    while left < w*maxfrac and cols[left] < thr: left += 1
    right = w
    while right > w*(1-maxfrac) and cols[right-1] < thr: right -= 1
    if (top, bot, left, right) != (0, h, 0, w) and (bot-top) > h*0.4 and (right-left) > w*0.4:
        return im.crop((left, top, right, bot))
    return im

def render(im, size=(450, 800)):
    w, h = im.size; r = h/w; tw, th = size; t = 9/16
    if r > t:
        nh = int(w/t); y = int((h-nh)*(0.04 if r >= 1.55 else 0.18))
        im = im.crop((0, y, w, y+nh))
    else:
        nw = int(h*t); x = (w-nw)//2
        im = im.crop((x, 0, x+nw, h))
    return ImageOps.fit(im, size, method=Image.LANCZOS)

for c in cands:
    try:
        r = requests.get(c["url"], headers=UA, timeout=120)
        r.raise_for_status()
        im = trim_borders(load(r.content))
        render(im).save(f"_tmp/prev6/{c['file']}", "JPEG", quality=82, optimize=True)
        out.append(c)
        print("ok", c["file"], im.size, flush=True)
    except Exception as e:
        print("err", c["file"], e, flush=True)
    time.sleep(0.2)
json.dump(out, open("_tmp/candidates6.json", "w"), indent=1)
print("TOTAL", len(out), flush=True)
