#!/usr/bin/env python3
"""Stage 3: drop wallpapers listed in _tmp/reject.json (ids) or _tmp/reject_files.json."""
import json, os
data = json.load(open("wallpapers.json", encoding="utf-8"))
rej = set(json.load(open("_tmp/reject.json")))
removed = []
for cat, items in data["categories"].items():
    keep = []
    for e in items:
        if e["id"] in rej:
            removed.append(e["id"])
            for suf in (".jpg", "_thumb.jpg"):
                fp = os.path.join(cat, e["id"] + suf)
                if os.path.exists(fp): os.remove(fp)
            continue
        keep.append(e)
    data["categories"][cat] = keep
for t, ids in list(data["tags"].items()):
    data["tags"][t] = [i for i in ids if i not in rej]
    if not data["tags"][t]:
        del data["tags"][t]
json.dump(data, open("wallpapers.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("removed", len(removed), removed)
