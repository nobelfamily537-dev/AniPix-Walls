#!/usr/bin/env python3
"""Render approved picks to 1080x1920 + thumb, then publish into wallpapers.json."""
import os, io, json, time, shutil
import requests, numpy as np
from PIL import Image, ImageFilter, ImageOps, ImageDraw

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
MODE = os.environ.get("MODE", "stage")
DATE = "2026-11-12"
FIN = "_tmp/night_final"
TARGET = 9/16

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
    col = np.convolve(a.mean(axis=0), np.ones(7)/7, "same")
    win = max(2, int(round(nw * gw / w)))
    xs = np.arange(len(col) - win + 1)
    if len(xs) <= 0:
        x = (w - nw) // 2
    else:
        centre = (len(col) - win) / 2
        bias = np.exp(-((xs - centre) ** 2) / (2 * (len(col) * 0.30) ** 2))
        scores = np.array([col[x:x+win].sum() for x in xs]) * bias
        x = int(xs[int(np.argmax(scores))] * w / gw)
    x = max(0, min(w - nw, x))
    return im.crop((x, 0, x + nw, h))

picks = json.load(open("_tmp/night_picks.json"))

if MODE == "stage":
    os.makedirs(FIN, exist_ok=True)
    made = []
    for p in picks:
        for attempt in range(3):
            try:
                r = requests.get(p["url"], headers=UA, timeout=180); r.raise_for_status()
                im = Image.open(io.BytesIO(r.content))
                if im.mode in ("RGBA", "LA", "P"):
                    im = im.convert("RGBA")
                    flat = Image.new("RGB", im.size, (255, 255, 255))
                    flat.paste(im, mask=im.split()[-1]); im = flat
                else:
                    im = im.convert("RGB")
                full = ImageOps.fit(smart_crop(im), (1080, 1920), method=Image.LANCZOS)
                full.save(os.path.join(FIN, p["id"] + ".jpg"), "JPEG", quality=95, optimize=True)
                th = full.resize((360, 640), Image.LANCZOS)
                th.save(os.path.join(FIN, p["id"] + "_thumb.jpg"), "JPEG", quality=80, optimize=True)
                made.append(p["id"])
                print("ok", p["id"], im.size, os.path.getsize(os.path.join(FIN, p["id"] + ".jpg"))//1024, "KB", flush=True)
                break
            except Exception as e:
                print("err", p["id"], e, flush=True); time.sleep(5)
    # review sheets: 5 finals per sheet, 2 cols
    ids = [m for m in made]
    cw, ch, cols = 380, 676, 2
    for s in range(0, len(ids), 4):
        chunk = ids[s:s+4]
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new("RGB", (cw*cols, ch*rows), (10, 10, 10))
        d = ImageDraw.Draw(sheet)
        for i, iid in enumerate(chunk):
            im = Image.open(os.path.join(FIN, iid + ".jpg")).resize((cw, ch), Image.LANCZOS)
            x, y = (i % cols)*cw, (i//cols)*ch
            sheet.paste(im, (x, y))
            d.rectangle([x, y, x+150, y+22], fill=(0, 0, 0))
            d.text((x+5, y+5), iid, fill=(255, 255, 0))
        sheet.save(os.path.join(FIN, f"sheet{s//4}.jpg"), "JPEG", quality=88)
    print("STAGED", len(made), flush=True)

else:
    approved = [p for p in picks if p["id"] in json.load(open("_tmp/night_approved.json"))]
    wp = json.load(open("wallpapers.json"))
    have = {e["id"] for c in wp["categories"].values() for e in c}
    have_urls = {e.get("full") for c in wp["categories"].values() for e in c}
    base = "https://raw.githubusercontent.com/nobelfamily537-dev/AniPix-Walls/main"
    added = 0
    for p in approved:
        cat, iid = p["cat"], p["id"]
        src_f = os.path.join(FIN, iid + ".jpg"); src_t = os.path.join(FIN, iid + "_thumb.jpg")
        if not (os.path.exists(src_f) and os.path.exists(src_t)):
            print("missing", iid, flush=True); continue
        if iid in have:
            print("dup id", iid, flush=True); continue
        full_url = f"{base}/{cat}/{iid}.jpg"
        if full_url in have_urls:
            print("dup url", iid, flush=True); continue
        os.makedirs(cat, exist_ok=True)
        shutil.copy(src_f, os.path.join(cat, iid + ".jpg"))
        shutil.copy(src_t, os.path.join(cat, iid + "_thumb.jpg"))
        wp["categories"][cat].insert(0, {
            "id": iid,
            "thumb": f"{base}/{cat}/{iid}_thumb.jpg",
            "full": full_url,
            "alt": full_url,
            "tags": p["tags"],
            "date": DATE,
        })
        have.add(iid); have_urls.add(full_url); added += 1
        print("added", cat, iid, flush=True)
    wp["version"] = int(wp.get("version", 0)) + 1
    wp["last_updated"] = DATE
    json.dump(wp, open("wallpapers.json", "w"), ensure_ascii=False, separators=(",", ":"))
    print("PUBLISHED", added, "version", wp["version"], flush=True)
