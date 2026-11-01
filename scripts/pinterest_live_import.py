#!/usr/bin/env python3
"""Download Pinterest VIDEO / GIF pins -> mp4 + 360x640 thumb -> live category.

Env:
  PINTEREST_URLS  entries separated by ';' (or whitespace). Each entry may carry
                  its own tags:  https://pin.it/abc|tag one~tag two
  CATEGORY        default: live
  TAGS            comma-separated tags forced on every item
"""
import os, re, json, html, time, hashlib, subprocess, shutil, tempfile
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
    "Accept": "text/html,application/xhtml+xml,image/avif,image/webp,*/*;q=0.8",
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
            return html.unescape(m.group(1))
    return ""


def unesc(s):
    return (s.replace("\\u002F", "/").replace("\\u002f", "/").replace("\\/", "/")
             .replace("&amp;", "&"))


def find_media(txt):
    """Return (url, 'mp4'|'gif') or ('','')."""
    t = unesc(txt)
    for prop in ("og:video:secure_url", "og:video:url", "og:video"):
        v = meta(t, prop)
        if v and ".mp4" in v:
            return v, "mp4"
    # any pinimg mp4 (quoted, then bare)
    for pat in (r'"(https://[A-Za-z0-9._\-]*pinimg\.com/[^"]+?\.mp4[^"]*)"',
                r'(https://[A-Za-z0-9._\-]*pinimg\.com/[^\s"\'<>\\]+?\.mp4)'):
        m = re.search(pat, t)
        if m:
            return m.group(1), "mp4"
    # gif pins
    for pat in (r'"(https://[A-Za-z0-9._\-]*pinimg\.com/[^"]+?\.gif)"',
                r'(https://[A-Za-z0-9._\-]*pinimg\.com/[^\s"\'<>\\]+?\.gif)'):
        m = re.search(pat, t)
        if m:
            return m.group(1), "gif"
    return "", ""


def make_thumb(mp4, out):
    if not FF:
        return False
    for ss in ("0.5", "1.5", "0"):
        cmd = [FF, "-y", "-loglevel", "error", "-ss", ss, "-i", mp4, "-frames:v", "1",
               "-vf", "scale=360:640:force_original_aspect_ratio=increase,crop=360:640",
               "-q:v", "3", out]
        if subprocess.run(cmd).returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 1500:
            return True
    return False


def gif_to_mp4(gif_path, mp4_path):
    if not FF:
        return False
    cmd = [FF, "-y", "-loglevel", "error", "-i", gif_path,
           "-movflags", "+faststart", "-pix_fmt", "yuv420p",
           "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", mp4_path]
    return subprocess.run(cmd).returncode == 0 and os.path.exists(mp4_path)


def split_entry(entry):
    if "|" in entry:
        u, t = entry.split("|", 1)
        return u.strip(), [x.strip().lower() for x in t.split("~") if x.strip()]
    return entry, []


added = []
for entry in URLS:
    url, own_tags = split_entry(entry)
    mp4 = None
    try:
        media, kind = "", ""
        for attempt_url in (url, url.rstrip("/") + "/"):
            r = requests.get(attempt_url, headers=UA, timeout=60, allow_redirects=True)
            r.raise_for_status()
            media, kind = find_media(r.text)
            if media:
                break
        if not media:
            print(f"SKIP (no video/gif found): {url}")
            continue

        wid = "pin" + hashlib.md5(media.encode()).hexdigest()[:10]
        if wid in existing:
            print(f"SKIP (already added): {wid}")
            continue

        vr = requests.get(media, headers=UA, timeout=180)
        vr.raise_for_status()
        mp4 = f"{CAT}/{wid}.mp4"
        if kind == "mp4":
            open(mp4, "wb").write(vr.content)
        else:
            with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as tf:
                tf.write(vr.content); gif = tf.name
            ok = gif_to_mp4(gif, mp4)
            os.remove(gif)
            if not ok:
                print(f"SKIP (gif->mp4 failed): {wid}")
                if os.path.exists(mp4): os.remove(mp4)
                continue

        if not os.path.exists(mp4) or os.path.getsize(mp4) < 40000:
            print(f"SKIP (video too small): {wid}")
            if os.path.exists(mp4): os.remove(mp4)
            continue

        th = f"{CAT}/{wid}_thumb.jpg"
        if not make_thumb(mp4, th):
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
        print(f"ADDED {wid} ({kind}) video={os.path.getsize(mp4)//1024}KB "
              f"thumb={os.path.getsize(th)//1024}KB tags={tags}")
        time.sleep(1)
    except Exception as e:
        print(f"ERROR {url}: {e}")
        if mp4 and os.path.exists(mp4):
            os.remove(mp4)
            print(f"  cleaned {mp4}")

json.dump(data, open("wallpapers.json", "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))
print(f"\nDONE: added {len(added)} live wallpaper(s): {added}")
