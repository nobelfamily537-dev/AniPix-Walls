#!/usr/bin/env python3
"""Drop meme-caption / empty-band picks from the 2026-11-13 batch."""
import json, os, subprocess

DROP = ["wpx3ebf69d6f9", "wpx821cad2ab6", "wpx0520598df4", "wpx28d84776c8"]
wp = json.load(open("wallpapers.json"))
idx = wp.setdefault("tags", {})
removed = set()
for cat, items in wp["categories"].items():
    keep = []
    for e in items:
        if e["id"] in DROP:
            removed.add(e["id"])
            for ext in (".jpg", "_thumb.jpg"):
                p = os.path.join(cat, e["id"] + ext)
                if os.path.exists(p):
                    subprocess.run(["git", "rm", "-q", "-f", p], check=False)
        else:
            keep.append(e)
    wp["categories"][cat] = keep
for t in list(idx):
    idx[t] = [x for x in idx[t] if x not in removed]
    if not idx[t]:
        del idx[t]
json.dump(wp, open("wallpapers.json", "w"), ensure_ascii=False, separators=(",", ":"))
print("removed", len(removed))
for f in ("_tmp/lcB/drop.py", "_tmp/lcB/trigger.txt", ".github/workflows/_tmp-lc-drop.yml"):
    if os.path.exists(f):
        subprocess.run(["git", "rm", "-q", "-f", f], check=False)
