#!/usr/bin/env python3
"""Remove QA-rejected entries from wallpapers.json and delete their image files."""
import json, os, subprocess

TODAY = "2026-11-16"
rejects = set(json.load(open("_tmp/lowrun17/rejects.json")))
data = json.load(open("wallpapers.json", encoding="utf-8"))

removed = 0
for cat, items in data["categories"].items():
    keep = []
    for e in items:
        if e["id"] in rejects:
            removed += 1
            for k in ("full", "thumb", "alt"):
                pass
        else:
            keep.append(e)
    data["categories"][cat] = keep

for tg, ids in list(data["tags"].items()):
    data["tags"][tg] = [i for i in ids if i not in rejects]
    if not data["tags"][tg]:
        del data["tags"][tg]

print("removed entries:", removed)
json.dump(data, open("wallpapers.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

for cat in ("anime", "anime2", "game", "nature"):
    for wid in rejects:
        for suffix in ("", "_thumb"):
            p = os.path.join(cat, "%s%s.jpg" % (wid, suffix))
            if os.path.exists(p):
                os.remove(p)
                print("deleted", p)

subprocess.run(["git", "add", "-A"], check=True)
subprocess.run(["git", "-c", "user.name=AniPix Bot", "-c", "user.email=nobelfamily537@gmail.com",
                "commit", "-m", "Wallpaper top-up - %s (QA: removed %d weak entries)" % (TODAY, removed)], check=True)
subprocess.run(["git", "push"], check=True)
print("pushed cleanup")
