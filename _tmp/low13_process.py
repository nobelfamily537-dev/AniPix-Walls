#!/usr/bin/env python3
"""Stage 2 (low-count run v13): download approved picks, render 1080x1920 q95 +
360x640 thumb, insert entries with rich tags, bump version, commit and push."""
import io, json, hashlib, os, re, subprocess, time, sys
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from PIL import Image, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Referer": "https://konachan.net/",
      "Accept": "image/avif,image/webp,image/*,*/*;q=0.8"}
RAW = "https://raw.githubusercontent.com/nobelfamily537-dev/AniPix-Walls/main"
NAME = "AniPix Bot"
MAIL = "nobelfamily537@gmail.com"
TODAY = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")

PICKS = sys.argv[1] if len(sys.argv) > 1 else "_tmp/pickslow13.json"


def art_box(im):
    import numpy as np
    a = np.asarray(im.convert("L"), dtype=np.float32)
    h, w = a.shape
    pr = np.percentile(a, 99, axis=1)
    pc = np.percentile(a, 99, axis=0)
    rows = np.where(pr > 45)[0]
    cols = np.where(pc > 45)[0]
    if len(rows) < 10 or len(cols) < 10:
        return im
    t, b = int(rows[0]), int(rows[-1]) + 1
    l, r = int(cols[0]), int(cols[-1]) + 1
    if (b - t) < h * 0.28 or (r - l) < w * 0.28:
        return im
    if (t, b, l, r) == (0, h, 0, w):
        return im
    return im.crop((l, t, r, b))


def render(im, focus=0.04):
    w, h = im.size
    ratio = h / w
    t = 16 / 9
    if ratio > 2.2:
        bg = ImageOps.fit(im, (1080, 1920), method=Image.LANCZOS).filter(ImageFilter.GaussianBlur(34))
        fg = im.copy()
        fg.thumbnail((1080, 1920), Image.LANCZOS)
        bg.paste(fg, ((1080 - fg.width) // 2, (1920 - fg.height) // 2))
        return bg
    if ratio > t:
        nh = int(w * t)
        y = int((h - nh) * (focus if ratio >= 1.55 else max(focus, 0.18)))
        im = im.crop((0, y, w, y + nh))
    else:
        nw = int(h / t)
        x = (w - nw) // 2
        im = im.crop((x, 0, x + nw, h))
    return ImageOps.fit(im, (1080, 1920), method=Image.LANCZOS)


picks = json.load(open(PICKS))
data = json.load(open("wallpapers.json", encoding="utf-8"))

existing_ids, existing_urls = set(), set()
for cat, items in data["categories"].items():
    for e in items:
        existing_ids.add(e["id"])
        for k in ("full", "thumb", "alt"):
            if e.get(k):
                existing_urls.add(e[k])

added, counts = [], {}
for p in picks:
    url = p["url"]
    cat = p["cat"]
    if url in existing_urls:
        print("SKIP dup url", url, flush=True)
        continue
    wid = "wpx" + hashlib.sha1(url.encode()).hexdigest()[:10]
    if wid in existing_ids:
        print("SKIP dup id", wid, flush=True)
        continue
    urls = []
    # ask the booru API for the sample url (small, fast) - avoids big file downloads
    for attempt in (1, 2):
        try:
            rr = requests.get("https://konachan.net/post.json", params={"tags": "id:%s" % p.get("pid")},
                              headers=UA, timeout=20)
            if rr.status_code == 200 and rr.json():
                js = rr.json()[0]
                for k in ("sample_url", "jpeg_url", "preview_url"):
                    if js.get(k):
                        urls.append(js[k])
                break
        except Exception as e:
            print("  api fail", type(e).__name__, flush=True)
        time.sleep(2)
    m2 = re.search(r"/([0-9a-f]{32})/", url)
    if m2 and "konachan" in url:
        urls.append("https://konachan.net/sample/%s/Konachan.com%%20-%%20%s%%20sample.jpg" % (m2.group(1), p.get("pid")))
    urls.append(url)
    content = None
    for u in urls:
        try:
            r = requests.get(u, headers=UA, timeout=40)
            if r.status_code == 200 and len(r.content) > 20000:
                content = r.content
                print("  got %dKB %s" % (len(content) // 1024, u[-40:]), flush=True)
                break
            print("  http", r.status_code, len(r.content), flush=True)
        except Exception as e:
            print("  dl fail", type(e).__name__, flush=True)
        time.sleep(1)
    if not content:
        print("SKIP download failed", url, flush=True)
        continue
    try:
        src = Image.open(io.BytesIO(content))
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
        if im.size[0] < 700:
            print("SKIP too small", url, im.size, flush=True)
            continue
        im = art_box(im)
        full = render(im, float(p.get("focus", 0.04)))
        os.makedirs(cat, exist_ok=True)
        full.save("%s/%s.jpg" % (cat, wid), "JPEG", quality=95, optimize=True, progressive=True)
        full.resize((360, 640), Image.LANCZOS).save("%s/%s_thumb.jpg" % (cat, wid), "JPEG",
                                                   quality=80, optimize=True, progressive=True)
    except Exception as e:
        print("ERR", url, e, flush=True)
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
    added.append([p["series"], wid, cat])
    counts[p["series"]] = counts.get(p["series"], 0) + 1
    print("ADDED", p["series"], wid, cat, len(tags), "tags", flush=True)
    time.sleep(0.2)

if added:
    data["version"] = int(data.get("version", 1)) + 1
    data["last_updated"] = TODAY
    json.dump(data, open("wallpapers.json", "w", encoding="utf-8"), ensure_ascii=False,
              separators=(",", ":"))
    json.dump(added, open("_tmp/last_added_low13.json", "w"))
    print("\nDONE added %d across %d series" % (len(added), len(counts)))
    print(json.dumps(counts, indent=1))
    subprocess.run(["git", "config", "sparse.expectFilesOutsideOfPatterns", "true"], check=False)
    subprocess.run(["git", "add", "--sparse", "wallpapers.json", "anime", "anime2",
                    "_tmp/pickslow13.json", "_tmp/last_added_low13.json"], check=True)
    msg = "Wallpaper top-up - %s (%d new across %d series)" % (TODAY, len(added), len(counts))
    subprocess.run(["git", "-c", "user.name=" + NAME, "-c", "user.email=" + MAIL,
                    "commit", "-m", msg], check=True)
    subprocess.run(["git", "push"], check=True)
    print("PUSHED:", msg)
else:
    print("NOTHING ADDED")
