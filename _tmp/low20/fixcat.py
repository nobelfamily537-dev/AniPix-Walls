#!/usr/bin/env python3
"""Move game-series wallpapers from the anime category to the game category."""
import hashlib, json, os, subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

TODAY = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
NAME, MAIL = "AniPix Bot", "nobelfamily537@gmail.com"

picks = json.load(open("_tmp/low20/picks.json"))
game_ids = set()
for p in picks:
    if p.get("cat") == "game":
        game_ids.add("wpx" + hashlib.sha1(p["url"].encode()).hexdigest()[:10])

data = json.load(open("wallpapers.json", encoding="utf-8"))
moved = []
keep = []
for e in data["categories"]["anime"]:
    if e["id"] in game_ids and e.get("date") == TODAY:
        e["thumb"] = e["thumb"].replace("/anime/", "/game/")
        e["full"] = e["full"].replace("/anime/", "/game/")
        if e.get("alt"):
            e["alt"] = e["alt"].replace("/anime/", "/game/")
        moved.append(e)
    else:
        keep.append(e)
data["categories"]["anime"] = keep
for e in reversed(moved):
    data["categories"]["game"].insert(0, e)

os.makedirs("game", exist_ok=True)
for e in moved:
    wid = e["id"]
    for suffix in (".jpg", "_thumb.jpg"):
        src, dst = "anime/%s%s" % (wid, suffix), "game/%s%s" % (wid, suffix)
        if os.path.exists(src):
            subprocess.run(["git", "mv", src, dst], check=True)
        else:
            print("missing", src)

data["version"] = int(data.get("version", 1)) + 1
data["last_updated"] = TODAY
json.dump(data, open("wallpapers.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("moved", len(moved), "game entries to the game category")

subprocess.run(["git", "add", "-A"], check=True)
subprocess.run(["git", "-c", "user.name=" + NAME, "-c", "user.email=" + MAIL, "commit", "-m",
                "Move %d game wallpapers to the game category - %s" % (len(moved), TODAY)], check=True)
subprocess.run(["git", "push"], check=True)
print("pushed")
