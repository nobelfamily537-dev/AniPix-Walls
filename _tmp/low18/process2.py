#!/usr/bin/env python3
"""Low-count run stage 2: process picks, add entries, commit per series."""
import io, json, os, random, re, subprocess, time
import requests
from PIL import Image, ImageFilter, ImageOps

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


def to_9x16(im):
    """Return 1080x1920 wallpaper. Crop when the source has enough pixels, else frame."""
    w, h = im.size
    r = h / w
    t = 16 / 9
    if r >= 1.0:
        if r >= t:
            nh = int(w * t)
            y = int((h - nh) * 0.04)
            im = im.crop((0, y, w, y + nh))
        else:
            nw = int(h / t)
            im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
        return im.resize((1080, 1920), Image.LANCZOS)
    # landscape
    if w >= 2400:
        nw = int(h / t)
        im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
        return im.resize((1080, 1920), Image.LANCZOS)
    # framed: blurred backdrop + sharp art
    bg = ImageOps.fit(im, (1080, 1920), method=Image.LANCZOS).filter(ImageFilter.GaussianBlur(48))
    bg = Image.eval(bg, lambda v: int(v * 0.72))
    fg = im.resize((1080, int(1080 * h / w)), Image.LANCZOS)
    y = (1920 - fg.height) // 2
    bg.paste(fg, (0, y))
    return bg


by_series = {}
order = []
for p in picks:
    by_series.setdefault(p["series"], []).append(p)
    if p["series"] not in order:
        order.append(p["series"])

total_new = 0
series_done = 0
for sname in order:
    added = 0
    for p in by_series[sname]:
        if p["url"] in existing:
            print("  dup url skip", p["url"], flush=True)
            continue
        try:
            r = requests.get(p["url"], headers=UA, timeout=120)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            im = to_9x16(im)
        except Exception as e:
            print("  FAIL", p["slug"], p["idx"], type(e).__name__, flush=True)
            continue
        wid = new_id()
        cat = p["cat"]
        d = os.path.join(".", cat)
        os.makedirs(d, exist_ok=True)
        im.save(os.path.join(d, wid + ".jpg"), "JPEG", quality=95, optimize=True)
        im.resize((360, 640), Image.LANCZOS).save(os.path.join(d, wid + "_thumb.jpg"), "JPEG", quality=80, optimize=True)
        full = "%s/%s/%s.jpg" % (RAW, cat, wid)
        thumb = "%s/%s/%s_thumb.jpg" % (RAW, cat, wid)
        tags = [t.strip().lower() for t in p["tags"] if t and t.strip()]
        tags = list(dict.fromkeys(tags))
        W["categories"][cat].append(dict(id=wid, thumb=thumb, full=full, alt=full,
                                         tags=",".join(tags), date=DATE))
        for t in tags:
            W["tags"].setdefault(t, []).append(wid)
        existing.add(p["url"])
        added += 1
        time.sleep(0.2)
    if added:
        total_new += added
        series_done += 1
        W["version"] = int(W["version"]) + 1
        W["last_updated"] = DATE
        with open("wallpapers.json", "w") as f:
            json.dump(W, f, ensure_ascii=False, separators=(",", ":"))
        subprocess.run(["git", "add", "-A", "wallpapers.json", "anime", "anime2"], check=False)
        msg = "Wallpaper top-up - %s (%d new across %d series)" % (DATE, added, 1)
        r = subprocess.run(["git", "commit", "-m", msg], capture_output=True, text=True)
        print(" commit:", r.returncode, (r.stdout + r.stderr)[:120].replace("\n", " "), flush=True)
        if r.returncode == 0:
            for attempt in range(3):
                pr = subprocess.run(["git", "push"], capture_output=True, text=True)
                if pr.returncode == 0:
                    print("  pushed", flush=True)
                    break
                print("  push retry", (pr.stderr or "")[:100].replace("\n", " "), flush=True)
                subprocess.run(["git", "pull", "--rebase", "-q"], capture_output=True)
                time.sleep(3)
    print("== %s: %d added" % (sname, added), flush=True)

print("DONE total %d across %d series, version %s" % (total_new, series_done, W["version"]), flush=True)
