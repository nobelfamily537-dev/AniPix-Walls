#!/usr/bin/env python3
"""Low-count run stage 2: process picked images, add entries, commit in batches."""
import io, json, os, random, re, subprocess, sys, time
import requests
from PIL import Image, ImageOps

OUT = "_tmp/low18"
DATE = "2026-11-20"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
      "Referer": "https://konachan.net/"}
RAW = "https://raw.githubusercontent.com/nobelfamily537-dev/AniPix-Walls/main"

picks = json.load(open(os.path.join(OUT, "picks.json")))
W = json.load(open("wallpapers.json"))

existing = set()
for cat in W["categories"].values():
    for e in cat:
        for k in ("full", "thumb", "alt"):
            if e.get(k):
                existing.add(e[k])
print("existing urls:", len(existing), flush=True)

have = set()
for cat in W["categories"].values():
    for e in cat:
        have.add(e["id"])


def new_id():
    while True:
        i = "wpx" + "".join(random.choice("0123456789abcdef") for _ in range(10))
        if i not in have:
            have.add(i)
            return i


def prep(im):
    w, h = im.size
    t = 16 / 9
    if h / w < 1.0:
        nw = int(h * t)
        im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
        w, h = im.size
    if h / w < t:
        nh = int(w * t)
        im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    elif h / w > 2.0:
        nw = int(h / t)
        im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(w * t)
        y = int((h - nh) * 0.04)
        im = im.crop((0, y, w, y + nh))
    return im.resize((1080, 1920), Image.LANCZOS)


def sh(*a):
    r = subprocess.run(a, capture_output=True, text=True)
    print(" ".join(a)[:90], "->", r.returncode, (r.stdout + r.stderr).strip()[:300], flush=True)
    return r


by_series = {}
for p in picks:
    by_series.setdefault(p["series"], []).append(p)

order = []
for p in picks:
    if p["series"] not in order:
        order.append(p["series"])

total_new = 0
series_done = 0
for sname in order:
    items = by_series[sname]
    added = 0
    for p in items:
        try:
            r = requests.get(p["url"], headers=UA, timeout=120)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            im = prep(im)
        except Exception as e:
            print("  FAIL", p["slug"], p["idx"], type(e).__name__, flush=True)
            continue
        wid = new_id()
        cat = p["cat"]
        d = os.path.join(".", cat)
        os.makedirs(d, exist_ok=True)
        im.save(os.path.join(d, wid + ".jpg"), "JPEG", quality=95, optimize=True)
        th = im.resize((360, 640), Image.LANCZOS)
        th.save(os.path.join(d, wid + "_thumb.jpg"), "JPEG", quality=80, optimize=True)
        full = "%s/%s/%s.jpg" % (RAW, cat, wid)
        thumb = "%s/%s/%s_thumb.jpg" % (RAW, cat, wid)
        tags = p["tags"]
        tags = [t.strip().lower() for t in tags if t and t.strip()]
        tags = list(dict.fromkeys(tags))
        W["categories"][cat].append(dict(id=wid, thumb=thumb, full=full, alt=full,
                                         tags=",".join(tags), date=DATE))
        for t in tags:
            W["tags"].setdefault(t, []).append(wid)
        added += 1
        time.sleep(0.2)
    if added:
        total_new += added
        series_done += 1
        W["version"] = int(W["version"]) + 1
        W["last_updated"] = DATE
        with open("wallpapers.json", "w") as f:
            json.dump(W, f, ensure_ascii=False, separators=(",", ":"))
        sh("git", "add", "-A", "wallpapers.json", "anime", "anime2", "game", "nature")
        msg = "Wallpaper top-up - %s (%d new across %d series)" % (DATE, added, 1)
        r = sh("git", "commit", "-m", msg)
        if r.returncode == 0:
            sh("git", "push")
    print("== %s: %d added" % (sname, added), flush=True)

print("DONE total %d across %d series, version %s" % (total_new, series_done, W["version"]), flush=True)
