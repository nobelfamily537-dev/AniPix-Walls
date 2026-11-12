#!/usr/bin/env python3
"""Append extra keywords to short-tag entries and keep the tag index in sync."""
import json

fix = json.load(open("_tmp/lc/tagfix.json"))
wp = json.load(open("wallpapers.json"))
tags_idx = wp.setdefault("tags", {})
ents = {}
for cat, items in wp["categories"].items():
    for e in items:
        ents[e["id"]] = e

changed = 0
for f in fix:
    e = ents.get(f["id"])
    if not e:
        print("missing", f["id"])
        continue
    cur = [t.strip() for t in e["tags"].split(",") if t.strip()]
    for t in [x.strip().lower() for x in f["extra"].split(",") if x.strip()]:
        if t and t not in cur and len(cur) < 15:
            cur.append(t)
    e["tags"] = ",".join(cur)
    for t in cur:
        lst = tags_idx.setdefault(t, [])
        if f["id"] not in lst:
            lst.append(f["id"])
    changed += 1
json.dump(wp, open("wallpapers.json", "w"), ensure_ascii=False, separators=(",", ":"))
print("updated", changed)
