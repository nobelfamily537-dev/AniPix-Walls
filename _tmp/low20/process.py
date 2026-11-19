#!/usr/bin/env python3
"""Low-count run (17:00 IST, 2026-11-16) stage 2: render picks, add entries, commit."""
import io, json, hashlib, os, subprocess, time
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from PIL import Image, ImageFilter, ImageOps

UA = {"User-Agent": "AniPixBot/1.0 (wallpaper curation)"}
RAW = "https://raw.githubusercontent.com/nobelfamily537-dev/AniPix-Walls/main"
NAME = "AniPix Bot"
MAIL = "nobelfamily537@gmail.com"
TODAY = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
PICKS = os.environ.get("PICKS", "_tmp/low20/picks.json")
OUT = "_tmp/low20"

DROP = {"highres", "absurdres", "huge_filesize", "incredibly_absurdres", "commentary", "commentary_request",
        "translated", "english_text", "text", "watermark", "signature", "artist_name", "dated", "bad_id",
        "twitter_username", "web_address", "logo", "border", "scan", "sample", "variant_set", "bad_pixiv_id",
        "bad_twitter_id", "bad_link", "md5_mismatch", "revision", "resolution_mismatch", "artist_request",
        "partial_commentary", "character_request", "check_translation", "hard_translated", "poor_translation",
        "game_cg", "screencap", "anime_screencap", "wallpaper", "wide_image", "phone_wallpaper",
        "official_art", "promotional_art", "key_visual", "poster", "banner", "album", "cover"}


def trim_uniform(im, thr=26, stdmax=9.0, maxfrac=0.45, step=0.01):
    g = im.convert("L")
    w, h = g.size
    box = [0, 0, w, h]

    def band_stats(rect):
        x0, y0, x1, y1 = rect
        band = g.crop((x0, y0, x1, y1))
        b = band.resize((1, band.size[1]))
        vals = list(b.getdata())
        m = sum(vals) / len(vals)
        var = sum((v - m) ** 2 for v in vals) / len(vals)
        return m, var ** 0.5

    for _ in range(int(maxfrac / step) * 2):
        changed = False
        for side in ("top", "bottom", "left", "right"):
            x0, y0, x1, y1 = box
            if side == "top":
                rect = (x0, y0, x1, y0 + max(2, int(h * step)))
            elif side == "bottom":
                rect = (x0, y1 - max(2, int(h * step)), x1, y1)
            elif side == "left":
                rect = (x0, y0, x0 + max(2, int(w * step)), y1)
            else:
                rect = (x1 - max(2, int(w * step)), y0, x1, y1)
            m, sd = band_stats(rect)
            if m < thr and sd < stdmax:
                if side == "top" and (y1 - rect[3]) > h * 0.4:
                    continue
                if side == "bottom" and (rect[1] - y0) > h * 0.4:
                    continue
                if side == "left" and (x1 - rect[2]) > w * 0.4:
                    continue
                if side == "right" and (rect[0] - x0) > w * 0.4:
                    continue
                box = list(rect) if side in ("top", "left") else (
                    [x0, y0, x1, rect[1]] if side == "bottom" else [x0, y0, rect[0], y1])
                changed = True
        if not changed:
            break
    if box != [0, 0, w, h]:
        return im.crop(tuple(box))
    return im


def trim_black_hard(im, thr=30, stdmax=20.0, maxfrac=0.5, step=0.01):
    return trim_uniform(im, thr=thr, stdmax=stdmax, maxfrac=maxfrac, step=step)


def bands_black(im, frac=0.05, thr=12.0, stdmax=3.5):
    """True only when BOTH the top and bottom edge bands are flat black (letterboxing)."""
    g = im.convert("L")
    w, h = g.size
    res = []
    for rect in ((0, 0, w, max(2, int(h * frac))), (0, h - max(2, int(h * frac)), w, h)):
        band = g.crop(rect).resize((1, max(2, int(h * frac))))
        vals = list(band.getdata())
        m = sum(vals) / len(vals)
        sd = (sum((v - m) ** 2 for v in vals) / len(vals)) ** 0.5
        res.append(m < thr and sd < stdmax)
    return res


def trim_strong(im):
    return trim_uniform(im, thr=45, stdmax=30.0, maxfrac=0.25, step=0.01)


def push(msg):
    subprocess.run(["git", "add", "-A"], check=True)
    r = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if r.returncode == 0:
        print("nothing to commit", flush=True)
        return
    subprocess.run(["git", "-c", "user.name=" + NAME, "-c", "user.email=" + MAIL,
                    "commit", "-m", msg], check=True)
    subprocess.run(["git", "push"], check=True)
    print("PUSHED:", msg, flush=True)


picks = json.load(open(PICKS))
data = json.load(open("wallpapers.json", encoding="utf-8"))

existing_ids = set()
existing_urls = set()
for cat, items in data["categories"].items():
    for e in items:
        existing_ids.add(e["id"])
        for k in ("full", "thumb", "alt"):
            if e.get(k):
                existing_urls.add(e[k])

counts, total = {}, 0
series_order = []
for p in picks:
    if p["series"] not in series_order:
        series_order.append(p["series"])
done_series = set()

for i, p in enumerate(picks):
    url = p["url"]
    cat = p.get("cat", "anime")
    if cat not in ("anime", "anime2"):
        cat = "anime"
    if url in existing_urls:
        print("SKIP dup url", url, flush=True)
        continue
    wid = "wpx" + hashlib.sha1(url.encode()).hexdigest()[:10]
    if wid in existing_ids:
        print("SKIP dup id", wid, flush=True)
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
        src0 = im.copy()
        full = None
        for trimmer in (trim_uniform, trim_black_hard, trim_strong):
            im = trimmer(src0.copy())
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
                if ratio > 1.0 / t:
                    nh = int(w / t)
                    y = int((h - nh) * float(p.get("focus", 0.04 if ratio >= 1.55 else 0.18)))
                    im = im.crop((0, y, w, y + nh))
                else:
                    nw = int(h * t)
                    x = int((w - nw) * float(p.get("fx", 0.5)))
                    im = im.crop((x, 0, x + nw, h))
                im = trimmer(im)
                full = ImageOps.fit(im, (1080, 1920), method=Image.LANCZOS)
            if not all(bands_black(full)):
                break
        if full is None or all(bands_black(full)):
            print("SKIP black band", url, flush=True)
            continue
        os.makedirs(cat, exist_ok=True)
        full.save("%s/%s.jpg" % (cat, wid), "JPEG", quality=95, optimize=True, progressive=True)
        full.resize((360, 640), Image.LANCZOS).save("%s/%s_thumb.jpg" % (cat, wid), "JPEG",
                                                   quality=80, optimize=True, progressive=True)
    except Exception as e:
        print("ERR", url, type(e).__name__, e, flush=True)
        continue

    tags = []
    for x in p.get("tags", []):
        x = x.strip().lower()
        if x and x not in tags:
            tags.append(x)
    tags = tags[:15]

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
    counts[p["series"]] = counts.get(p["series"], 0) + 1
    total += 1
    print("ADDED", p["series"], wid, cat, len(tags), "tags", flush=True)

    # commit every time we finish a series (keeps earlier work safe)
    nxt = series_order.index(p["series"]) + 1
    remaining = [q for q in picks[i + 1:] if q["series"] != p["series"]]
    if not remaining:
        done_series.add(p["series"])
        json.dump(data, open("wallpapers.json", "w", encoding="utf-8"), ensure_ascii=False,
                  separators=(",", ":"))
        m = len(counts)
        if nxt >= len(series_order):
            msg = "Wallpaper top-up - %s (%d new across %d series)" % (TODAY, total, m)
        else:
            msg = "Wallpaper top-up - %s (partial: %d new across %d series)" % (TODAY, total, m)
        push(msg)
    time.sleep(0.2)

data["version"] = int(data.get("version", 1)) + 1
data["last_updated"] = TODAY
json.dump(data, open("wallpapers.json", "w", encoding="utf-8"), ensure_ascii=False,
          separators=(",", ":"))
print("\nDONE added %d across %d series" % (total, len(counts)), flush=True)
print(json.dumps(counts, indent=1), flush=True)
json.dump(counts, open(os.path.join(OUT, "result_counts.json"), "w"), indent=1)
push("Wallpaper top-up - %s (%d new across %d series)" % (TODAY, total, len(counts)))
