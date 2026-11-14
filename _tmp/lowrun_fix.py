#!/usr/bin/env python3
"""Fix pass: move anime2-intended entries out of 'anime', top up short tag lists."""
import os, json, hashlib, shutil, subprocess
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
TODAY = datetime.now(IST).strftime("%Y-%m-%d")
REPO = "nobelfamily537-dev/AniPix-Walls"
RAW = f"https://raw.githubusercontent.com/{REPO}/main"
FILL = ["anime", "anime art", "portrait", "phone wallpaper", "wallpaper"]


def git(*a):
    subprocess.run(["git"] + list(a), check=True)


git("config", "user.email", "nobelfamily537@gmail.com")
git("config", "user.name", "AniPix Bot")

picks = json.load(open("_tmp/lowrun/picks.json"))
data = json.load(open("wallpapers.json", encoding="utf-8"))
idx = {}
for cat, lst in data["categories"].items():
    for e in lst:
        idx[e["id"]] = (cat, e)

moved = 0
for p in picks:
    wid = "wpx" + hashlib.md5(p["url"].encode()).hexdigest()[:10]
    if wid not in idx:
        print("missing", wid)
        continue
    cat, entry = idx[wid]
    if cat == p["cat"]:
        continue
    if cat != "anime" or p["cat"] != "anime2":
        print("skip move", wid, cat, "->", p["cat"])
        continue
    os.makedirs("anime2", exist_ok=True)
    for suffix in (".jpg", "_thumb.jpg"):
        src, dst = f"anime/{wid}{suffix}", f"anime2/{wid}{suffix}"
        if os.path.exists(src):
            shutil.move(src, dst)
    entry["thumb"] = f"{RAW}/anime2/{wid}_thumb.jpg"
    entry["full"] = f"{RAW}/anime2/{wid}.jpg"
    entry["alt"] = f"{RAW}/anime2/{wid}.jpg"
    data["categories"]["anime"].remove(entry)
    data["categories"]["anime2"].insert(0, entry)
    moved += 1

print("moved to anime2:", moved)

# top up short tag lists (accuracy-safe generic descriptors only)
topped = 0
for cat, lst in data["categories"].items():
    for e in lst:
        if e.get("date") != TODAY:
            continue
        tags = [t for t in e["tags"].split(",") if t]
        if len(tags) >= 10:
            continue
        for f in FILL:
            if len(tags) >= 10:
                break
            if f not in tags:
                tags.append(f)
                data["tags"].setdefault(f, [])
                if e["id"] not in data["tags"][f]:
                    data["tags"][f].insert(0, e["id"])
        e["tags"] = ",".join(tags)
        topped += 1

print("tag lists topped up:", topped)
data["last_updated"] = TODAY
json.dump(data, open("wallpapers.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
git("add", "-A", "wallpapers.json", "anime", "anime2", "game")
git("commit", "-m", "Fix category split for 2026-11-14 low-count top-up (%d moved to anime2)" % moved)
for _ in range(4):
    try:
        git("push", "origin", "main")
        break
    except subprocess.CalledProcessError:
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=False)
print("done")
