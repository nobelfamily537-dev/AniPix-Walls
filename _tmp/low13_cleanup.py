import json, os, subprocess
from datetime import datetime
from zoneinfo import ZoneInfo
TODAY = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
rm = set(json.load(open("_tmp/low13_remove.json")))
data = json.load(open("wallpapers.json", encoding="utf-8"))
removed = 0
for cat, items in data["categories"].items():
    keep = []
    for e in items:
        if e["id"] in rm:
            for p in ("%s/%s.jpg" % (cat, e["id"]), "%s/%s_thumb.jpg" % (cat, e["id"])):
                if os.path.exists(p):
                    os.remove(p)
            removed += 1
        else:
            keep.append(e)
    data["categories"][cat] = keep
for tg, ids in list(data["tags"].items()):
    n = [i for i in ids if i not in rm]
    if not n:
        del data["tags"][tg]
    else:
        data["tags"][tg] = n
data["last_updated"] = TODAY
json.dump(data, open("wallpapers.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("removed", removed)
subprocess.run(["git", "config", "sparse.expectFilesOutsideOfPatterns", "true"], check=False)
subprocess.run(["git", "add", "--sparse", "-u", "anime", "anime2"], check=True)
subprocess.run(["git", "add", "wallpapers.json", "_tmp/low13_remove.json"], check=True)
subprocess.run(["git", "-c", "user.name=AniPix Bot", "-c", "user.email=nobelfamily537@gmail.com",
                "commit", "-m", "Remove low-quality picks - %s (%d dropped)" % (TODAY, removed)], check=True)
subprocess.run(["git", "push"], check=True)
print("PUSHED")
