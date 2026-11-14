#!/usr/bin/env python3
"""Low-count run: publish curated picks into the repo (images + wallpapers.json)."""
import os, io, json, time, re, hashlib, subprocess
from datetime import datetime, timezone, timedelta
import requests
from PIL import Image, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
REPO = os.environ.get("GITHUB_REPOSITORY", "nobelfamily537-dev/AniPix-Walls")
BRANCH = "main"
RAW = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}"
IST = timezone(timedelta(hours=5, minutes=30))
TODAY = datetime.now(IST).strftime("%Y-%m-%d")

DROP = {"highres", "absurdres", "lowres", "huge_filesize", "commentary", "commentary_request",
        "translated", "english_text", "text", "twitter_username", "web_address", "artist_name",
        "signature", "watermark", "bad_id", "bad_pixiv_id", "scan", "official_art", "screencap",
        "1girl", "1boy", "2girls", "2boys", "solo", "multiple_girls", "male_focus", "female",
        "looking_at_viewer", "simple_background", "white_background", "transparent_background",
        "high_quality", "anime", "anime_style", "digital_media_(artwork)", "wallpaper", "16:9_aspect_ratio",
        "4:3_aspect_ratio", "absurdres", "banner", "border", "english_commentary", "dated"}


def render(im, size):
    tw, th = size
    t = tw / th
    w, h = im.size
    if w / h > t:
        nw = int(h * t)
        x = (w - nw) // 2
        im = im.crop((x, 0, x + nw, h))
    else:
        nh = int(w / t)
        y = int((h - nh) * (0.08 if h / w < 2.05 else 0.0))
        im = im.crop((0, y, w, y + nh))
    return im.resize((tw, th), Image.LANCZOS)


def clean_tags(series_tag, alt, src_tags, extra_ok=()):
    out = [series_tag]
    if alt and alt.lower() != series_tag.lower():
        out.append(alt.lower())
    for t in src_tags:
        t = str(t).replace("_", " ").strip().lower()
        if not t or len(t) < 3 or t in DROP:
            continue
        if re.search(r"\d{2,4}:\d{2,4}", t):
            continue
        if t in out:
            continue
        out.append(t)
        if len(out) >= 13:
            break
    for e in extra_ok:
        if e not in out:
            out.append(e)
    return out[:15]


def git(*args):
    subprocess.run(["git"] + list(args), check=True)


git("config", "user.email", "nobelfamily537@gmail.com")
git("config", "user.name", "AniPix Bot")

picks = json.load(open("_tmp/lowrun/picks.json"))
data = json.load(open("wallpapers.json", encoding="utf-8"))
existing = set()
for cat, lst in data["categories"].items():
    for e in lst:
        existing.add(e["id"])
        existing.add(e.get("full", ""))
        existing.add(e.get("thumb", ""))

order = []
for p in picks:
    if p["series"] not in order:
        order.append(p["series"])

report = {}
BATCH = 4
batch_no, batch_new, batch_series = 1, 0, 0
made = 0

for si, series in enumerate(order):
    items = [p for p in picks if p["series"] == series]
    cat = items[0]["cat"]
    os.makedirs(cat, exist_ok=True)
    added = 0
    for p in items:
        try:
            r = requests.get(p["url"], headers=UA, timeout=90)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            if im.width < 500 or im.height < 700:
                print("skip small", p["pid"], im.size, flush=True)
                continue
            wid = "wpx" + hashlib.md5(p["url"].encode()).hexdigest()[:10]
            if wid in existing:
                print("skip dup", wid, flush=True)
                continue
            full = render(im, (1080, 1920))
            full.save(f"{cat}/{wid}.jpg", "JPEG", quality=95, optimize=True, progressive=True)
            full.resize((360, 640), Image.LANCZOS).save(
                f"{cat}/{wid}_thumb.jpg", "JPEG", quality=80, optimize=True, progressive=True)
            tags = clean_tags(p["tag"], p.get("alt", ""), p.get("tags", []),
                              extra_ok=["anime wallpaper"])
            entry = {
                "id": wid,
                "thumb": f"{RAW}/{cat}/{wid}_thumb.jpg",
                "full": f"{RAW}/{cat}/{wid}.jpg",
                "alt": f"{RAW}/{cat}/{wid}.jpg",
                "tags": ",".join(tags),
                "date": TODAY,
            }
            data["categories"][cat].insert(0, entry)
            for t in tags:
                data["tags"].setdefault(t, [])
                if wid not in data["tags"][t]:
                    data["tags"][t].insert(0, wid)
            existing.add(wid)
            added += 1
            made += 1
            time.sleep(0.1)
        except Exception as e:
            print("err", p.get("pid"), type(e).__name__, str(e)[:80], flush=True)

    report[series] = added
    batch_new += added
    batch_series += 1
    print("%s: %d added" % (series, added), flush=True)

    # commit every 4 series so a late failure keeps earlier work
    if batch_series >= BATCH or si == len(order) - 1:
        data["version"] = int(data.get("version", 1)) + 1
        data["last_updated"] = TODAY
        json.dump(data, open("wallpapers.json", "w", encoding="utf-8"),
                  ensure_ascii=False, separators=(",", ":"))
        git("add", "-A", "wallpapers.json", "anime", "anime2", "game")
        msg = ("Wallpaper top-up - %s (%d new across %d series) [part %d]"
               % (TODAY, batch_new, batch_series, batch_no))
        git("commit", "-m", msg)
        for attempt in range(4):
            try:
                git("push", "origin", BRANCH)
                break
            except subprocess.CalledProcessError:
                time.sleep(5)
                subprocess.run(["git", "pull", "--rebase", "origin", BRANCH], check=False)
        print("committed:", msg, flush=True)
        batch_no += 1
        batch_new, batch_series = 0, 0

json.dump(report, open("_tmp/lowrun/report.json", "w"), indent=1)
print("TOTAL ADDED", made, flush=True)
