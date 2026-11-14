#!/usr/bin/env python3
"""Night3 render + publish: trim padding, crop 9:16, write category files, update wallpapers.json."""
import os, io, json, time, shutil
import requests, numpy as np
from PIL import Image, ImageFilter, ImageOps, ImageDraw

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
MODE = os.environ.get("MODE", "stage")
DATE = "2026-11-14"
FIN = "_tmp/n3_final"
SH = "_tmp/n3_final_sheets"
TARGET = 9 / 16
base = "https://raw.githubusercontent.com/nobelfamily537-dev/AniPix-Walls/main"

def trim_borders(im):
    g = np.asarray(im.convert("L"), dtype=np.float32)
    h, w = g.shape
    def dark_row(i): return g[i].mean() < 20 and g[i].std() < 14
    def dark_col(j): return g[:, j].mean() < 20 and g[:, j].std() < 14
    t = 0
    while t < int(h * 0.45) and dark_row(t): t += 1
    b = h - 1
    while b > int(h * 0.55) and dark_row(b): b -= 1
    l = 0
    while l < int(w * 0.45) and dark_col(l): l += 1
    r = w - 1
    while r > int(w * 0.55) and dark_col(r): r -= 1
    if (b - t + 1) * (r - l + 1) < 0.35 * w * h:
        return im
    if t == 0 and b == h - 1 and l == 0 and r == w - 1:
        return im
    print(f"    trimmed t{t} b{h-1-b} l{l} r{w-1-r}", flush=True)
    return im.crop((l, t, r + 1, b + 1))

def smart_crop(im):
    w, h = im.size
    r = h / w
    if r > TARGET * 1.02:
        nh = int(w / TARGET); y = int((h - nh) * 0.05)
        return im.crop((0, y, w, y + nh))
    if r >= TARGET:
        return im
    nw = int(h * TARGET)
    gw = 200
    g = im.convert("L").resize((gw, max(20, int(gw * h / w))), Image.LANCZOS)
    a = np.asarray(g.filter(ImageFilter.FIND_EDGES), dtype=np.float32)
    col = np.convolve(a.mean(axis=0), np.ones(7) / 7, "same")
    win = max(2, int(round(nw * gw / w)))
    xs = np.arange(len(col) - win + 1)
    if len(xs) <= 0:
        x = (w - nw) // 2
    else:
        centre = (len(col) - win) / 2
        bias = np.exp(-((xs - centre) ** 2) / (2 * (len(col) * 0.30) ** 2))
        scores = np.array([col[x:x + win].sum() for x in xs]) * bias
        x = int(xs[int(np.argmax(scores))] * w / gw)
    x = max(0, min(w - nw, x))
    return im.crop((x, 0, x + nw, h))

def render(url, out_full, out_thumb):
    r = requests.get(url, headers=UA, timeout=180); r.raise_for_status()
    im = Image.open(io.BytesIO(r.content))
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        a = np.asarray(im.split()[-1])
        frac = float((a < 250).mean())
        if frac > 0.02:
            raise ValueError(f"transparent {frac:.2f}")
        im = im.convert("RGB")
    else:
        im = im.convert("RGB")
    im = trim_borders(im)
    full = ImageOps.fit(smart_crop(im), (1080, 1920), method=Image.LANCZOS)
    full.save(out_full, "JPEG", quality=95, optimize=True)
    full.resize((360, 640), Image.LANCZOS).save(out_thumb, "JPEG", quality=80, optimize=True)
    return full

if MODE == "stage":
    stage = json.load(open("_tmp/n3_stage.json"))
    os.makedirs(FIN, exist_ok=True); os.makedirs(SH, exist_ok=True)
    made = []
    for p in stage:
        f = os.path.join(FIN, p["id"] + ".jpg"); t = os.path.join(FIN, p["id"] + "_thumb.jpg")
        if os.path.exists(f) and os.path.exists(t):
            made.append(p["id"]); continue
        try:
            render(p["url"], f, t)
            made.append(p["id"])
            print("ok", p["id"], p["series"], os.path.getsize(f) // 1024, "KB", flush=True)
        except Exception as e:
            print("skip", p["id"], p["series"], e, flush=True)
    cw, ch, cols = 400, 711, 4
    for s in range(0, len(made), 4):
        chunk = made[s:s + 4]
        sheet = Image.new("RGB", (cw * len(chunk), ch), (10, 10, 10))
        d = ImageDraw.Draw(sheet)
        for i, iid in enumerate(chunk):
            im = Image.open(os.path.join(FIN, iid + ".jpg")).resize((cw, ch), Image.LANCZOS)
            sheet.paste(im, (i * cw, 0))
            d.rectangle([i * cw, 0, i * cw + 110, 18], fill=(0, 0, 0))
            d.text((i * cw + 4, 4), iid, fill=(255, 255, 0))
        sheet.save(os.path.join(SH, f"s{s//4:02d}.jpg"), "JPEG", quality=88)
    json.dump(made, open("_tmp/n3_made.json", "w"))
    print("STAGED", len(made), flush=True)

else:
    picks = json.load(open("_tmp/n3_picks.json"))
    wp = json.load(open("wallpapers.json"))
    have = {e["id"] for c in wp["categories"].values() for e in c}
    have_urls = {e.get("full") for c in wp["categories"].values() for e in c}
    added = []
    for p in picks:
        cat, iid = p["cat"], p["id"]
        src_f = os.path.join(FIN, iid + ".jpg"); src_t = os.path.join(FIN, iid + "_thumb.jpg")
        full_url = f"{base}/{cat}/{iid}.jpg"
        if iid in have or full_url in have_urls:
            print("dup", iid, flush=True); continue
        if not (os.path.exists(src_f) and os.path.exists(src_t)):
            print("missing", iid, flush=True); continue
        os.makedirs(cat, exist_ok=True)
        shutil.copy(src_f, os.path.join(cat, iid + ".jpg"))
        shutil.copy(src_t, os.path.join(cat, iid + "_thumb.jpg"))
        wp["categories"][cat].insert(0, {
            "id": iid, "thumb": f"{base}/{cat}/{iid}_thumb.jpg",
            "full": full_url, "alt": full_url, "tags": p["tags"], "date": DATE})
        have.add(iid); have_urls.add(full_url); added.append(iid)
        print("added", cat, iid, flush=True)
    wp["version"] = int(wp.get("version", 0)) + 1
    wp["last_updated"] = DATE
    json.dump(wp, open("wallpapers.json", "w"), ensure_ascii=False, separators=(",", ":"))
    open("_tmp/n3_count.txt", "w").write(str(len(added)))
    print("PUBLISHED", len(added), "version", wp["version"], flush=True)
