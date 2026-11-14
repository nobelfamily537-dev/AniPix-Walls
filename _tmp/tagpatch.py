import json, subprocess
from datetime import datetime, timezone, timedelta
IST = timezone(timedelta(hours=5, minutes=30))
TODAY = datetime.now(IST).strftime("%Y-%m-%d")
ADD = {
 "wpx287386cc41": ["blonde hair", "white dress", "purple roses", "letter"],
 "wpxfbc228d1e4": ["blonde hair", "blue jacket", "letter", "white dress"],
 "wpx9d1ac67712": ["spiky hair", "red headband", "green eyes", "black jacket"],
}
d = json.load(open("wallpapers.json", encoding="utf-8"))
idx = {}
for cat, lst in d["categories"].items():
    for e in lst:
        idx[e["id"]] = e
for wid, extra in ADD.items():
    e = idx.get(wid)
    if not e:
        print("missing", wid); continue
    tags = [t for t in e["tags"].split(",") if t]
    for t in extra:
        if t in tags or len(tags) >= 14:
            continue
        tags.append(t)
        d["tags"].setdefault(t, [])
        if wid not in d["tags"][t]:
            d["tags"][t].insert(0, wid)
    e["tags"] = ",".join(tags)
    print(wid, len(tags))
d["last_updated"] = TODAY
json.dump(d, open("wallpapers.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
def git(*a): subprocess.run(["git"] + list(a), check=True)
git("config", "user.email", "nobelfamily537@gmail.com")
git("config", "user.name", "AniPix Bot")
git("add", "-A", "wallpapers.json")
git("commit", "-m", "Top up tags on three 2026-11-14 wallpapers")
git("push", "origin", "main")
import os
for p in ("_tmp/tagpatch.py", ".github/workflows/tagpatch.yml"):
    if os.path.exists(p): os.remove(p)
subprocess.run(["git", "add", "-A"], check=True)
subprocess.run(["git", "commit", "-m", "chore: remove tag patch helper"], check=False)
subprocess.run(["git", "push", "origin", "main"], check=False)
print("done")
