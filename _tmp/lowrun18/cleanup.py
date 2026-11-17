#!/usr/bin/env python3
"""Lowrun18 stage 3: remove low-quality entries from this run, fix bad tags, push."""
import json, os, subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

TODAY = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
NAME, MAIL = "AniPix Bot", "nobelfamily537@gmail.com"

# indices into the audit sheet order (cands order = wallpapers.json insert order reversed)
DROP_IDX = [0, 1, 2, 5, 7, 10, 13, 15, 24, 27, 30, 33, 36, 37, 38, 39, 42, 48, 50, 52, 55, 62, 64, 67, 73]

ids = json.load(open("newids.json"))
drop_ids = {ids[i] for i in DROP_IDX}

data = json.load(open("wallpapers.json", encoding="utf-8"))
removed = []
for cat, items in data["categories"].items():
    keep = []
    for e in items:
        if e["id"] in drop_ids:
            removed.append((cat, e["id"]))
            for suf in (".jpg", "_thumb.jpg"):
                p = "%s/%s%s" % (cat, e["id"], suf)
                if os.path.exists(p):
                    os.remove(p)
        else:
            keep.append(e)
    data["categories"][cat] = keep

# rebuild tag index
tags = {}
for cat, items in data["categories"].items():
    for e in items:
        for t in [x.strip() for x in e.get("tags", "").split(",") if x.strip()]:
            tags.setdefault(t, [])
            if e["id"] not in tags[t]:
                tags[t].append(e["id"])
data["tags"] = tags

# fix two bad tags from the source metadata
FIX = {"risa": "lisa", "maomao (kusuriya no h": "maomao"}
for cat, items in data["categories"].items():
    for e in items:
        if not any(f in e.get("tags", "") for f in FIX):
            continue
        parts = []
        for t in [x.strip() for x in e["tags"].split(",") if x.strip()]:
            t = FIX.get(t, t)
            if t not in parts:
                parts.append(t)
        e["tags"] = ",".join(parts)
tags = {}
for cat, items in data["categories"].items():
    for e in items:
        for t in [x.strip() for x in e.get("tags", "").split(",") if x.strip()]:
            tags.setdefault(t, [])
            if e["id"] not in tags[t]:
                tags[t].append(e["id"])
data["tags"] = tags

data["version"] = int(data.get("version", 1)) + 1
data["last_updated"] = TODAY
json.dump(data, open("wallpapers.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

print("removed", len(removed), flush=True)
print(sorted(r[1] for r in removed), flush=True)

subprocess.run(["git", "add", "-A"], check=True)
subprocess.run(["git", "-c", "user.name=" + NAME, "-c", "user.email=" + MAIL, "commit",
                "-m", "Wallpaper top-up - %s (quality pass: removed %d)" % (TODAY, len(removed))],
               check=True)
subprocess.run(["git", "push"], check=True)
print("PUSHED", flush=True)
