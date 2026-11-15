#!/usr/bin/env python3
"""Night gap-fill fix 2: drop one too-revealing image, rebalance categories."""
import json, os, subprocess

REMOVE = ["wpxe81c029e84"]
MOVE = [("wpx9000f71b6e", "anime2", "anime")]

data = json.load(open("wallpapers.json"))
for cat, arr in data["categories"].items():
    keep = []
    for w in arr:
        if w["id"] in REMOVE:
            for f in ("%s/%s.jpg" % (cat, w["id"]), "%s/%s_thumb.jpg" % (cat, w["id"])):
                if os.path.exists(f):
                    subprocess.run(["git", "rm", "-q", f], check=False)
        else:
            keep.append(w)
    data["categories"][cat] = keep

for wid, src, dst in MOVE:
    ent = [w for w in data["categories"][src] if w["id"] == wid]
    if not ent:
        continue
    e = ent[0]
    data["categories"][src] = [w for w in data["categories"][src] if w["id"] != wid]
    base = "https://raw.githubusercontent.com/nobelfamily537-dev/AniPix-Walls/main/%s/%s" % (dst, wid)
    e["full"] = base + ".jpg"
    e["alt"] = base + ".jpg"
    e["thumb"] = base + "_thumb.jpg"
    data["categories"][dst].append(e)
    for f in ("%s/%s.jpg" % (src, wid), "%s/%s_thumb.jpg" % (src, wid)):
        if os.path.exists(f):
            os.makedirs(dst, exist_ok=True)
            subprocess.run(["git", "mv", f, "%s/%s" % (dst, os.path.basename(f))], check=False)

for t, ids in list(data.get("tags", {}).items()):
    new = [i for i in ids if i not in REMOVE]
    if new:
        data["tags"][t] = new
    else:
        del data["tags"][t]

json.dump(data, open("wallpapers.json", "w"), ensure_ascii=False, separators=(",", ":"))
print("anime", len(data["categories"]["anime"]), "anime2", len(data["categories"]["anime2"]))
