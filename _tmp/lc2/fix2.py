#!/usr/bin/env python3
"""Fix series-tag casing and top up short tag lists; then remove tooling."""
import json, os, subprocess

CANON = {"nikke": "Nikke", "honkai star rail": "Honkai Star Rail"}
FILL = ["anime wallpaper", "mobile wallpaper", "vertical", "phone wallpaper", "wallpaper"]

wp = json.load(open("wallpapers.json"))
tags_idx = wp.setdefault("tags", {})
ents = []
for cat, items in wp["categories"].items():
    for e in items:
        if e.get("date") == "2026-11-13":
            ents.append(e)

for e in ents:
    tags = [t.strip() for t in e["tags"].split(",") if t.strip()]
    tags = [CANON.get(t, t) for t in tags]
    seen = []
    for t in tags:
        if t not in seen:
            seen.append(t)
    for f in FILL:
        if len(seen) >= 10:
            break
        if f not in seen:
            seen.append(f)
    e["tags"] = ",".join(seen[:15])

ids = {e["id"] for e in ents}
for e in ents:
    for t in [x.strip() for x in e["tags"].split(",") if x.strip()]:
        lst = tags_idx.setdefault(t, [])
        if e["id"] not in lst:
            lst.append(e["id"])

for k in ("nikke", "honkai star rail"):
    if k in tags_idx:
        rest = [i for i in tags_idx[k] if i not in ids]
        if rest:
            tags_idx[k] = rest
        else:
            del tags_idx[k]

json.dump(wp, open("wallpapers.json", "w"), ensure_ascii=False, separators=(",", ":"))

for p in ("_tmp/lc2/fix2.py", "_tmp/lc2/trigger-fix2.txt",
          ".github/workflows/_tmp-lc-fix2.yml"):
    if os.path.exists(p):
        subprocess.run(["git", "rm", "-q", "-f", p], check=False)
print("ok")
