#!/usr/bin/env python3
"""Remove wallpapers that failed quality review."""
import json, os, subprocess, sys
from datetime import datetime
from zoneinfo import ZoneInfo

TODAY = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
REMOVE = json.load(open(os.environ.get("REMOVE", "_tmp/lowrun15/remove.json")))
data = json.load(open("wallpapers.json", encoding="utf-8"))

removed = 0
for wid in REMOVE:
    for cat, items in data["categories"].items():
        for e in list(items):
            if e["id"] == wid:
                items.remove(e)
                for suffix in ("", "_thumb"):
                    p = "%s/%s%s.jpg" % (cat, wid, suffix)
                    if os.path.exists(p):
                        os.remove(p)
                        print("rm", p, flush=True)
                removed += 1
                break
    for tag, ids in list(data["tags"].items()):
        if wid in ids:
            ids.remove(wid)
            if not ids:
                del data["tags"][tag]

if removed:
    data["version"] = int(data.get("version", 1)) + 1
    data["last_updated"] = TODAY
    json.dump(data, open("wallpapers.json", "w", encoding="utf-8"), ensure_ascii=False,
              separators=(",", ":"))
    subprocess.run(["git", "add", "-A"], check=True)
    subprocess.run(["git", "-c", "user.name=AniPix Bot", "-c", "user.email=nobelfamily537@gmail.com",
                    "commit", "-m", "Remove %d low-quality wallpapers - %s" % (removed, TODAY)], check=True)
    subprocess.run(["git", "push"], check=True)
    print("REMOVED", removed, flush=True)
else:
    print("NOTHING REMOVED", flush=True)
