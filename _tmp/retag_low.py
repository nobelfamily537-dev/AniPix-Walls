#!/usr/bin/env python3
"""Apply richer tag sets to the ids listed in _tmp/retag.json and rebuild the tag index."""
import json

data = json.load(open("wallpapers.json", encoding="utf-8"))
upd = {x["id"]: [t.strip().lower() for t in x["tags"].split(",") if t.strip()] for x in json.load(open("_tmp/retag.json"))}

# strip these ids out of the whole index first
for tg, ids in list(data["tags"].items()):
    data["tags"][tg] = [i for i in ids if i not in upd]

n = 0
for cat, items in data["categories"].items():
    for e in items:
        if e["id"] in upd:
            toks, seen = [], set()
            for t in upd[e["id"]]:
                if t not in seen:
                    seen.add(t); toks.append(t)
            e["tags"] = ",".join(toks)
            for t in toks:
                data["tags"].setdefault(t, [])
                if e["id"] not in data["tags"][t]:
                    data["tags"][t].insert(0, e["id"])
            n += 1
print("retagged", n)
json.dump(data, open("wallpapers.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
