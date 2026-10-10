#!/usr/bin/env python3
"""Convert existing static wallpapers into small MP4 live wallpapers.

Env:
  SOURCE_PATHS  space-separated repo paths, e.g. "game/pindcbdfc4ae8.jpg"
  TAGS          comma-separated tags to attach
  DURATION      seconds per clip (default 6)
"""
import os, re, json, subprocess, sys
from PIL import Image

SOURCES = [p.strip() for p in os.environ.get("SOURCE_PATHS", "").split() if p.strip()]
TAGS = [t.strip().lower() for t in os.environ.get("TAGS", "").split(",") if t.strip()]
DUR = int(os.environ.get("DURATION", "6") or 6)
REPO = os.environ.get("GITHUB_REPOSITORY", "nobelfamily537-dev/AniPix-Walls")
BRANCH = os.environ.get("BRANCH", "main")
RAW = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}"

WJ = "wallpapers.json"
data = json.load(open(WJ, encoding="utf-8"))
live = data.setdefault("categories", {}).setdefault("live", [])
data.setdefault("tags", {})
os.makedirs("live", exist_ok=True)


def make_mp4(src, out):
    """Slow Ken-Burns zoom -> 1080x1920 h264, small file."""
    vf = ("scale=1080:1920:force_original_aspect_ratio=increase,"
          "crop=1080:1920,"
          "zoompan=z='min(zoom+0.0009,1.30)'"
          f":d={DUR*25}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
          ":s=1080x1920:fps=25")
    cmd = ["ffmpeg", "-y", "-loop", "1", "-i", src, "-vf", vf,
           "-t", str(DUR), "-an", "-c:v", "libx264", "-preset", "slow",
           "-crf", "30", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True, capture_output=True)


done = []
for src in SOURCES:
    try:
        if not os.path.exists(src):
            print(f"SKIP (missing): {src}"); continue
        wid = os.path.splitext(os.path.basename(src))[0]          # e.g. pindcbdfc4ae8
        mp4 = f"live/{wid}.mp4"
        make_mp4(src, mp4)
        Image.open(src).convert("RGB").resize((360, 640), Image.LANCZOS).save(
            f"live/{wid}_thumb.jpg", "JPEG", quality=80, optimize=True)

        # remove from whatever category it was in
        for cat, arr in data["categories"].items():
            if cat == "live":
                continue
            for e in list(arr):
                if e.get("id") == wid:
                    arr.remove(e)
                    print(f"  removed {wid} from {cat}")
                    t = f"{cat}/{wid}.jpg"
                    if os.path.exists(t):
                        os.remove(t)
                    tt = f"{cat}/{wid}_thumb.jpg"
                    if os.path.exists(tt):
                        os.remove(tt)

        live.insert(0, {
            "id": wid,
            "thumb": f"{RAW}/live/{wid}_thumb.jpg",
            "full": f"{RAW}/live/{wid}.mp4",
            "alt": f"{RAW}/live/{wid}.mp4",
            "tags": ", ".join(TAGS) if TAGS else "live",
            "isLive": True,
            "video": True,
        })
        for t in (TAGS + ["live"]):
            data["tags"].setdefault(t, [])
            if wid not in data["tags"][t]:
                data["tags"][t].insert(0, wid)
        size = os.path.getsize(mp4)
        done.append(wid)
        print(f"LIVE {wid}  {size/1024:.0f} KB  tags={sorted(set(TAGS+['live']))}")
    except Exception as e:
        print(f"ERROR {src}: {e}")

json.dump(data, open(WJ, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(f"\nDONE: {len(done)} live wallpaper(s): {done}")
