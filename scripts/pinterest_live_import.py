#!/usr/bin/env python3
"""Download Pinterest VIDEO pins, make a 360x640 thumb with ffmpeg, add to a
live/video category in wallpapers.json.

Env:
  PINTEREST_URLS  space-separated pin / pin.it URLs
  CATEGORY        default: live
  TAGS            comma-separated tags to force
"""
import os, re, json, html, time, hashlib, subprocess, shutil
import requests

def ffmpeg_bin():
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None

FF = ffmpeg_bin()
print("ffmpeg:", FF)

_raw = os.environ.get("PINTEREST_URLS", "")
# ";" separates entries (lets tags contain spaces); otherwise split on whitespace
URLS = ([u.strip() for u in _raw.split(";") if u.strip()] if ";" in _raw
        else [u.strip() for u in _raw.split() if u.strip()])
CAT = (os.environ.get("CATEGORY", "live").strip() or "live")
FORCE_TAGS = [t.strip().lower() for t in os.environ.get("TAGS", "").split(",") if t.strip()]
REPO = os.environ.get("GITHUB_REPOSITORY", "nobelfamily537-dev/AniPix-Walls")
BRANCH = os.environ.get("BRANCH", "main")
RAW = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}"

UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

os.makedirs(CAT, exist_ok=True)
data = json.load(open("wallpapers.json", encoding="utf-8"))
data.setdefault("categories", {}).setdefault(CAT, [])
data.setdefault("tags", {})
existing = {e["id"] for e in data["categories"][CAT]}


def meta(txt, prop):
    for pat in (rf'property=["\']{prop}["\'][^>]*content=["\']([^"\']+)',
                rf'content=["\']([^"\']+)["\'][^>]*property=["\']{prop}["\']'):
        m = re.search(pat, txt)
        if m:
            return html.unescape(m.group(1)).replace("\\/", "/")
    return ""


def find_video(txt):
    for prop in ("og:video:secure_url", "og:video:url", "og:video"):
        v = meta(txt, prop)
        if v and ".mp4" in v:
            return v
    m = re.search(r'"(https://v1\.pinimg\.com/videos/[^"]+?\.mp4)"', txt)
    if m:
        return m.group(1).replace("\\/", "/")
    m = re.search(r'"(https://[^"]+?\.mp4)"', txt)
    return m.group(1).replace("\\/", "/") if m else ""


def thumb(mp4, out):
    """First decent frame -> 360x640 cover crop."""
    if not FF:
        return False
    for ss in ("0.5", "1.5", "0"):
        cmd = [FF, "-y", "-loglevel", "error", "-ss", ss, "-i", mp4,
               "-frames:v", "1", "-vf",
               "scale=360:640:force_original_aspect_ratio=increase,crop=360:640",
               "-q:v", "3", out]
        if subprocess.run(cmd).returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 1500:
            return True
    return False


added = []
# PER-URL TAGS: "url|tag one~tag two"  (~ separates tags so spaces are allowed)
def split_entry(entry):
    if "|" in entry:
        u, t = entry.split("|", 1)
        return u.strip(), [x.strip().lower() for x in t.split("~") if x.strip()]
    return entry, []

for entry in URLS:
    url, own_tags = split_entry(entry)
    try:
        r = requests.get(url, headers=UA, timeout=60, allow_redirects=True)
        r.raise_for_status()
        vid = find_video(r.text)
        if not vid:
            print(f"SKIP (no video found): {url}")
            continue
        wid = "pin" + hashlib.md5(vid.encode()).hexdigest()[:10]
        if wid in existing:
            print(f"SKIP (already added): {wid}")
            continue

        vr = requests.get(vid, headers=UA, timeout=180)
        vr.raise_for_status()
        mp4 = f"{CAT}/{wid}.mp4"
        open(mp4, "wb").write(vr.content)
        if os.path.getsize(mp4) < 40000:
            print(f"SKIP (video too small): {wid}")
            os.remove(mp4)
            continue

        th = f"{CAT}/{wid}_thumb.jpg"
        if not thumb(mp4, th):
            print(f"SKIP (thumb failed): {wid}")
            os.remove(mp4)
            continue

        tags = sorted(set(["pinterest", "live wallpaper", "video"] + FORCE_TAGS + own_tags))
        data["categories"][CAT].insert(0, {
            "id": wid,
            "thumb": f"{RAW}/{CAT}/{wid}_thumb.jpg",
            "full": f"{RAW}/{CAT}/{wid}.mp4",
            "alt": f"{RAW}/{CAT}/{wid}.mp4",
            "tags": ",".join(tags),
            "isLive": True,
            "video": True,
        })
        for t in tags:
            data["tags"].setdefault(t, [])
            if wid not in data["tags"][t]:
                data["tags"][t].insert(0, wid)
        existing.add(wid)
        added.append(wid)
        print(f"ADDED {wid}  video={os.path.getsize(mp4)//1024}KB  thumb={os.path.getsize(th)//1024}KB  tags={tags}")
        time.sleep(1)
    except Exception as e:
        print(f"ERROR {url}: {e}")
        for f in os.listdir(CAT):
            if f.endswith(".mp4") and f[:-4] not in existing and not os.path.exists(f"{CAT}/{f[:-4]}_thumb.jpg"):
                os.remove(f"{CAT}/{f}")
                print(f"  cleaned orphan {f}")

json.dump(data, open("wallpapers.json", "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))
print(f"\nDONE: added {len(added)} live wallpaper(s): {added}")
