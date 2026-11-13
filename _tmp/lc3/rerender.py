#!/usr/bin/env python3
"""Re-render transparent-PNG picks onto a blur-fill background; drop rejects."""
import json, io, os, subprocess, time
import requests
from PIL import Image, ImageFilter, ImageEnhance

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
cfg = json.load(open("_tmp/lc3/rerender.json"))
wp = json.load(open("wallpapers.json"))
tags_idx = wp.setdefault("tags", {})
ents = {}
for cat, items in wp["categories"].items():
    for e in items:
        ents[e["id"]] = (cat, e)

# --- removals ---
for rid in cfg.get("remove", []):
    if rid in ents:
        cat, e = ents[rid]
        for ext in (".jpg", "_thumb.jpg"):
            p = os.path.join(cat, rid + ext)
            if os.path.exists(p):
                subprocess.run(["git", "rm", "-q", "-f", p], check=False)
        wp["categories"][cat].remove(e)
        for t in list(tags_idx):
            tags_idx[t] = [x for x in tags_idx[t] if x != rid]
            if not tags_idx[t]:
                del tags_idx[t]
        print("removed", rid)

def fetch(key):
    if key.startswith("wh"):
        wid = key[2:]
        for ext in ("jpg", "png"):
            u = f"https://w.wallhaven.cc/full/{wid[:2]}/wallhaven-{wid}.{ext}"
            try:
                r = requests.get(u, headers=UA, timeout=60)
                if r.status_code == 200 and len(r.content) > 20000:
                    return r.content
            except Exception as e:
                print("  err", e)
        return None
    if key.startswith("sb"):
        sid = key[2:]
        try:
            r = requests.get("https://safebooru.org/index.php", params={
                "page": "dapi", "s": "post", "q": "index", "json": "1", "id": sid, "limit": "1"},
                headers=UA, timeout=60)
            data = r.json()
            if data:
                url = data[0].get("file_url")
                r2 = requests.get(url, headers=UA, timeout=60)
                if r2.status_code == 200:
                    return r2.content
        except Exception as e:
            print("  err", e)
    return None

def render(raw):
    im = Image.open(io.BytesIO(raw))
    im.load()
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    alpha = im.split()[-1]
    hist = alpha.histogram()
    transparent = sum(hist[:12]) / float(im.width * im.height)
    if transparent < 0.06:
        return None, transparent
    bbox = alpha.getbbox()
    if not bbox:
        return None, transparent
    cut = im.crop(bbox)
    # background: cover-scaled blurred version of the cutout itself
    bg = Image.new("RGB", cut.size, (18, 18, 24))
    bg.paste(cut, mask=cut.split()[-1])
    scale = max(1080 / bg.width, 1920 / bg.height)
    bg = bg.resize((max(1080, int(bg.width * scale) + 1), max(1920, int(bg.height * scale) + 1)), Image.LANCZOS)
    x = (bg.width - 1080) // 2
    y = (bg.height - 1920) // 2
    bg = bg.crop((x, y, x + 1080, y + 1920))
    bg = bg.filter(ImageFilter.GaussianBlur(42))
    bg = ImageEnhance.Brightness(bg).enhance(0.62)
    bg = ImageEnhance.Color(bg).enhance(0.9)
    # place the cutout contained with a small margin
    s = min((1080 * 0.96) / cut.width, (1920 * 0.94) / cut.height)
    fg = cut.resize((max(1, int(cut.width * s)), max(1, int(cut.height * s))), Image.LANCZOS)
    canvas = bg.copy()
    px = (1080 - fg.width) // 2
    py = int((1920 - fg.height) * 0.45)
    canvas.paste(fg, (px, py), fg.split()[-1])
    return canvas, transparent

done = skipped = 0
for it in cfg["items"]:
    i, cat, key = it["id"], it["cat"], it["key"]
    if i not in ents:
        print("missing", i)
        continue
    raw = fetch(key)
    if not raw:
        print("no source", i, key)
        continue
    out, tr = render(raw)
    if out is None:
        skipped += 1
        continue
    full = out.resize((1080, 1920), Image.LANCZOS)
    thumb = full.resize((360, 640), Image.LANCZOS)
    full.save(os.path.join(cat, i + ".jpg"), "JPEG", quality=95, optimize=True, progressive=True)
    thumb.save(os.path.join(cat, i + "_thumb.jpg"), "JPEG", quality=80, optimize=True, progressive=True)
    done += 1
    print("re-rendered", i, key, round(tr, 2))
    time.sleep(0.5)

json.dump(wp, open("wallpapers.json", "w"), ensure_ascii=False, separators=(",", ":"))
print("done", done, "skipped", skipped)
for p in ("_tmp/lc3/rerender.py", "_tmp/lc3/rerender.json", "_tmp/lc3/trigger-rr.txt",
          ".github/workflows/_tmp-lc-rr.yml"):
    if os.path.exists(p):
        subprocess.run(["git", "rm", "-q", "-f", p], check=False)
