#!/usr/bin/env python3
"""Stage 2: download picked images, crop to 9:16, save 1080x1920 q95 + 360x640 thumb,
insert wallpapers.json entries with tags/date, bump version."""
import io, json, hashlib, os, sys, time
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from PIL import Image, ImageFilter, ImageOps

UA = {"User-Agent": "AniPixBot/1.0 (wallpaper curation)"}
RAW = "https://raw.githubusercontent.com/nobelfamily537-dev/AniPix-Walls/main"
TODAY = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
picks = json.load(open("_tmp/picks.json"))
data = json.load(open("wallpapers.json", encoding="utf-8"))

existing_urls = set()
existing_ids = set()
for cat, items in data["categories"].items():
    for e in items:
        existing_ids.add(e["id"])
        for k in ("full", "thumb", "alt"):
            if e.get(k): existing_urls.add(e[k])
known_tags = set(data["tags"].keys())

added = []
for p in picks:
    url = p["url"]
    cat = p["cat"]
    if url in existing_urls:
        print("SKIP dup url", url); continue
    wid = "wpx" + hashlib.sha1(url.encode()).hexdigest()[:10]
    force = bool(p.get("force"))
    if wid in existing_ids and not force:
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
        w, h = im.size
        r = h / w
        t = 9/16
        if r > 2.05:
            bg = ImageOps.fit(im, (1080, 1920), method=Image.LANCZOS).filter(ImageFilter.GaussianBlur(30))
            fg = im.copy(); fg.thumbnail((1080, 1920), Image.LANCZOS)
            bg.paste(fg, ((1080-fg.width)//2, (1920-fg.height)//2))
            full = bg
        else:
            if r > t:
                if r >= 1.55:
                    nh = int(w/t); y = int((h-nh)*float(p.get("focus", 0.04))); im = im.crop((0, y, w, y+nh))
                else:
                    nh = int(w/t); y = int((h-nh)*0.18); im = im.crop((0, y, w, y+nh))
            else:
                nw = int(h*t); x = (w-nw)//2; im = im.crop((x, 0, x+nw, h))
            full = ImageOps.fit(im, (1080, 1920), method=Image.LANCZOS)
        os.makedirs(cat, exist_ok=True)
        full.save(f"{cat}/{wid}.jpg", "JPEG", quality=95, optimize=True, progressive=True)
        full.resize((360, 640), Image.LANCZOS).save(f"{cat}/{wid}_thumb.jpg", "JPEG", quality=80, optimize=True, progressive=True)
    except Exception as e:
        print("ERR", url, e); continue

    if wid in existing_ids:
        # refresh files of an existing entry, keep its position
        for cat2, items in data["categories"].items():
            for e in items:
                if e["id"] == wid:
                    e["date"] = TODAY
        added.append((p["series"], wid, cat, "refreshed"))
        print("REFRESHED", wid)
        continue
    tags = [t.strip().lower() for t in p["tags"].split(",") if t.strip()]
    # keep only sane tags, dedupe preserving order
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
    added.append((p["series"], wid, cat))
    print("ADDED", p["series"], wid, cat, len(tags), "tags")
    time.sleep(0.3)

if added:
    data["version"] = int(data.get("version", 1)) + 1
    data["last_updated"] = TODAY
json.dump(data, open("wallpapers.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(f"\nDONE added {len(added)}")
json.dump(added, open("_tmp/last_added.json", "w"))
