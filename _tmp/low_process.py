#!/usr/bin/env python3
"""Stage 2 (low-count run): download picks, render 1080x1920 q95 + 360x640 thumb,
insert entries with rich tags, bump version, commit and push."""
import io, json, hashlib, os, subprocess, sys, time
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from PIL import Image, ImageFilter, ImageOps

UA = {"User-Agent": "AniPixBot/1.0 (wallpaper curation)"}
RAW = "https://raw.githubusercontent.com/nobelfamily537-dev/AniPix-Walls/main"
NAME = "AniPix Bot"
MAIL = "nobelfamily537@gmail.com"

TODAY = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")


def trim_borders(im, thr=24, maxfrac=0.35):
    g = im.convert("L")
    w, h = g.size
    rows = list(g.resize((1, h)).getdata())
    cols = list(g.resize((w, 1)).getdata())
    top = 0
    while top < h * maxfrac and rows[top] < thr:
        top += 1
    bot = h
    while bot > h * (1 - maxfrac) and rows[bot - 1] < thr:
        bot -= 1
    left = 0
    while left < w * maxfrac and cols[left] < thr:
        left += 1
    right = w
    while right > w * (1 - maxfrac) and cols[right - 1] < thr:
        right -= 1
    if (top, bot, left, right) != (0, h, 0, w) and (bot - top) > h * 0.4 and (right - left) > w * 0.4:
        return im.crop((left, top, right, bot))
    return im


picks = json.load(open("_tmp/pickslow.json"))
data = json.load(open("wallpapers.json", encoding="utf-8"))

existing_ids = set()
existing_urls = set()
for cat, items in data["categories"].items():
    for e in items:
        existing_ids.add(e["id"])
        for k in ("full", "thumb", "alt"):
            if e.get(k):
                existing_urls.add(e[k])

added = []
counts = {}
for p in picks:
    url = p["url"]
    cat = p["cat"]
    if url in existing_urls:
        print("SKIP dup url", url)
        continue
    wid = "wpx" + hashlib.sha1(url.encode()).hexdigest()[:10]
    if wid in existing_ids:
        print("SKIP dup id", wid)
        continue
    try:
        r = requests.get(url, headers=UA, timeout=180)
        r.raise_for_status()
        src = Image.open(io.BytesIO(r.content))
        if src.mode in ("RGBA", "LA", "P"):
            src = src.convert("RGBA")
            bbox = src.getbbox()
            if bbox:
                src = src.crop(bbox)
            flat = Image.new("RGB", src.size, (255, 255, 255))
            flat.paste(src, mask=src.split()[-1])
            im = flat
        else:
            im = src.convert("RGB")
        w, h = im.size
        ratio = h / w
        t = 9 / 16
        if ratio > 2.05:
            bg = ImageOps.fit(im, (1080, 1920), method=Image.LANCZOS).filter(ImageFilter.GaussianBlur(30))
            fg = im.copy()
            fg.thumbnail((1080, 1920), Image.LANCZOS)
            bg.paste(fg, ((1080 - fg.width) // 2, (1920 - fg.height) // 2))
            full = bg
        else:
            if ratio > t:
                nh = int(w / t)
                y = int((h - nh) * float(p.get("focus", 0.04 if ratio >= 1.55 else 0.18)))
                im = im.crop((0, y, w, y + nh))
            else:
                nw = int(h * t)
                x = (w - nw) // 2
                im = im.crop((x, 0, x + nw, h))
            im = trim_borders(im)
            full = ImageOps.fit(im, (1080, 1920), method=Image.LANCZOS)
        os.makedirs(cat, exist_ok=True)
        full.save("%s/%s.jpg" % (cat, wid), "JPEG", quality=95, optimize=True, progressive=True)
        full.resize((360, 640), Image.LANCZOS).save("%s/%s_thumb.jpg" % (cat, wid), "JPEG",
                                                   quality=80, optimize=True, progressive=True)
    except Exception as e:
        print("ERR", url, e)
        continue

    tags = [x.strip().lower() for x in p["tags"].split(",") if x.strip()]
    seen = set()
    tags = [x for x in tags if not (x in seen or seen.add(x))]
    data["categories"][cat].insert(0, {
        "id": wid,
        "thumb": "%s/%s/%s_thumb.jpg" % (RAW, cat, wid),
        "full": "%s/%s/%s.jpg" % (RAW, cat, wid),
        "alt": "%s/%s/%s.jpg" % (RAW, cat, wid),
        "tags": ",".join(tags),
        "date": TODAY,
    })
    for tg in tags:
        data["tags"].setdefault(tg, [])
        if wid not in data["tags"][tg]:
            data["tags"][tg].insert(0, wid)
    existing_ids.add(wid)
    existing_urls.add(url)
    added.append((p["series"], wid, cat))
    counts[p["series"]] = counts.get(p["series"], 0) + 1
    print("ADDED", p["series"], wid, cat, len(tags), "tags", flush=True)
    time.sleep(0.2)

if added:
    data["version"] = int(data.get("version", 1)) + 1
    data["last_updated"] = TODAY
    json.dump(data, open("wallpapers.json", "w", encoding="utf-8"), ensure_ascii=False,
              separators=(",", ":"))
    print("\nDONE added %d across %d series" % (len(added), len(counts)))
    print(json.dumps(counts, indent=1))
    json.dump(added, open("_tmp/last_added_low.json", "w"))
    subprocess.run(["git", "add", "-A"], check=True)
    msg = "Wallpaper top-up - %s (%d new across %d series)" % (TODAY, len(added), len(counts))
    subprocess.run(["git", "-c", "user.name=" + NAME, "-c", "user.email=" + MAIL,
                    "commit", "-m", msg], check=True)
    subprocess.run(["git", "push"], check=True)
    print("PUSHED:", msg)
else:
    print("NOTHING ADDED")
