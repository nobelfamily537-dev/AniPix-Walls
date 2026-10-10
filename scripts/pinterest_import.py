#!/usr/bin/env python3
"""Download Pinterest images, process them, and add to the AniPix wallpapers.json.

Env:
  PINTEREST_URLS  space-separated pin / pin.it / i.pinimg.com URLs
  CATEGORY        repo folder + wallpapers.json category (default: anime)
  TAGS            comma-separated tags to attach
"""
import os, re, io, json, sys, time, hashlib
import requests
from PIL import Image, ImageOps

URLS = [u.strip() for u in os.environ.get("PINTEREST_URLS", "").split() if u.strip()]
CAT = (os.environ.get("CATEGORY", "anime").strip() or "anime")
TAGS = [t.strip().lower() for t in os.environ.get("TAGS", "").split(",") if t.strip()]
REPO = os.environ.get("GITHUB_REPOSITORY", "nobelfamily537-dev/AniPix-Walls")
BRANCH = os.environ.get("BRANCH", "main")
RAW = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}"

UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,image/avif,image/webp,image/*,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

os.makedirs(CAT, exist_ok=True)
WJ = "wallpapers.json"
data = json.load(open(WJ, encoding="utf-8"))
data.setdefault("categories", {}).setdefault(CAT, [])
data.setdefault("tags", {})
existing_ids = {e["id"] for e in data["categories"][CAT]}


def image_url(u):
    """Resolve a Pinterest pin link to a direct image URL."""
    if "pinimg.com" in u:
        return u
    r = requests.get(u, headers=UA, timeout=60, allow_redirects=True)
    r.raise_for_status()
    html = r.text
    for pat in (r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)',
                r'content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']',
                r'"og:image"\s*:\s*"([^"]+)"'):
        m = re.search(pat, html)
        if m:
            return m.group(1).replace("\\/", "/")
    return None


def crop_9x16(im, yfocus=0.30):
    w, h = im.size
    t = 9 / 16
    if w / h > t:
        nw = int(h * t); x = (w - nw) // 2
        return im.crop((x, 0, x + nw, h))
    nh = int(w / t); y = int((h - nh) * yfocus)
    return im.crop((0, y, w, y + nh))


added = []
for url in URLS:
    try:
        img = image_url(url)
        if not img:
            print(f"SKIP (no og:image): {url}"); continue
        resp = requests.get(img, headers=UA, timeout=90)
        resp.raise_for_status()
        im = Image.open(io.BytesIO(resp.content)).convert("RGB")
        if im.width < 600 or im.height < 800:
            print(f"SKIP (too small {im.size}): {url}"); continue

        wid = "pin" + hashlib.md5(img.encode()).hexdigest()[:10]
        if wid in existing_ids:
            print(f"SKIP (already added): {wid}"); continue

        full = ImageOps.fit(crop_9x16(im), (1080, 1920), method=Image.LANCZOS)
        full.save(f"{CAT}/{wid}.jpg", "JPEG", quality=92, optimize=True, progressive=True)
        thumb = full.resize((360, 640), Image.LANCZOS)
        thumb.save(f"{CAT}/{wid}_thumb.jpg", "JPEG", quality=80, optimize=True, progressive=True)

        data["categories"][CAT].insert(0, {
            "id": wid,
            "thumb": f"{RAW}/{CAT}/{wid}_thumb.jpg",
            "full": f"{RAW}/{CAT}/{wid}.jpg",
            "alt": f"{RAW}/{CAT}/{wid}.jpg",
        })
        for t in TAGS:
            data["tags"].setdefault(t, [])
            if wid not in data["tags"][t]:
                data["tags"][t].insert(0, wid)
        existing_ids.add(wid)
        added.append(wid)
        print(f"ADDED {wid}  ({CAT})  <- {img[:80]}")
        time.sleep(1)
    except Exception as e:
        print(f"ERROR {url}: {e}")

json.dump(data, open(WJ, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(f"\nDONE: added {len(added)} wallpaper(s): {added}")
