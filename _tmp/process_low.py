#!/usr/bin/env python3
"""Stage 2 (low-count run): download picked images, crop 9:16, save 1080x1920 q95 + 360x640 thumb,
insert wallpapers.json entries with tags/date. Env: PICKS, FINAL (1 = bump version)."""
import io, json, hashlib, os, time
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from PIL import Image, ImageFilter, ImageOps

UA = {"User-Agent": "AniPixBot/1.0 (wallpaper curation)"}
RAW = "https://raw.githubusercontent.com/nobelfamily537-dev/AniPix-Walls/main"
PICKS = os.environ.get("PICKS", "_tmp/picks_low.json")
FINAL = os.environ.get("FINAL", "0") == "1"

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

TODAY = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
picks = json.load(open(PICKS))
data = json.load(open("wallpapers.json", encoding="utf-8"))

existing_urls, existing_ids = set(), set()
for cat, items in data["categories"].items():
    for e in items:
        existing_ids.add(e["id"])
        for k in ("full", "thumb", "alt"):
            if e.get(k): existing_urls.add(e[k])

added = []
for p in picks:
    url, cat = p["url"], p["cat"]
    if url in existing_urls:
        print("SKIP dup url", url); continue
    wid = "wpx" + hashlib.sha1(url.encode()).hexdigest()[:10]
    if wid in existing_ids:
        print("SKIP dup id", wid); continue
    try:
        r = requests.get(url, headers=UA, timeout=120)
        r.raise_for_status()
        src = Image.open(io.BytesIO(r.content))
        if src.mode in ("RGBA", "LA", "P"):
            src = src.convert("RGBA")
            bbox = src.getbbox()
            if bbox: src = src.crop(bbox)
            flat = Image.new("RGB", src.size, (255, 255, 255))
            flat.paste(src, mask=src.split()[-1])
            im = flat
        else:
            im = src.convert("RGB")
        if im.width < 700 or im.height < 900:
            print("SKIP too small", im.size, url); continue
        w, h = im.size
        rr = h / w
        t = 9/16
        if rr > 2.05:
            bg = ImageOps.fit(im, (1080, 1920), method=Image.LANCZOS).filter(ImageFilter.GaussianBlur(30))
            fg = im.copy(); fg.thumbnail((1080, 1920), Image.LANCZOS)
            bg.paste(fg, ((1080-fg.width)//2, (1920-fg.height)//2))
            full = bg
        else:
            if rr > t:
                nh = int(w/t); y = int((h-nh)*float(p.get("focus", 0.04))); im = im.crop((0, y, w, y+nh))
            else:
                nw = int(h*t); x = (w-nw)//2; im = im.crop((x, 0, x+nw, h))
            im = trim_borders(im)
            full = ImageOps.fit(im, (1080, 1920), method=Image.LANCZOS)
        os.makedirs(cat, exist_ok=True)
        full.save(f"{cat}/{wid}.jpg", "JPEG", quality=95, optimize=True, progressive=True)
        full.resize((360, 640), Image.LANCZOS).save(f"{cat}/{wid}_thumb.jpg", "JPEG", quality=80, optimize=True, progressive=True)
    except Exception as e:
        print("ERR", url, e); continue

    tags = [x.strip().lower() for x in p["tags"].split(",") if x.strip()]
    seen = set(); tags = [x for x in tags if not (x in seen or seen.add(x))]
    data["categories"][cat].insert(0, {
        "id": wid,
        "thumb": f"{RAW}/{cat}/{wid}_thumb.jpg",
        "full": f"{RAW}/{cat}/{wid}.jpg",
        "alt": f"{RAW}/{cat}/{wid}.jpg",
        "tags": ",".join(tags),
        "date": TODAY,
    })
    for tg in tags:
        data["tags"].setdefault(tg, [])
        if wid not in data["tags"][tg]:
            data["tags"][tg].insert(0, wid)
    existing_ids.add(wid); existing_urls.add(url)
    added.append({"series": p["series"], "id": wid, "cat": cat})
    print("ADDED", p["series"], wid, cat, len(tags), "tags", flush=True)
    time.sleep(0.2)

if added and FINAL:
    data["version"] = int(data.get("version", 1)) + 1
    data["last_updated"] = TODAY
json.dump(data, open("wallpapers.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(f"\nDONE added {len(added)} (final={FINAL})")
json.dump(added, open("_tmp/last_added_low.json", "w"), indent=1)
