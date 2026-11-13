#!/usr/bin/env python3
"""Final pass: drop the one image with an artist signature, clean up temp files."""
import os, json, shutil

DATE = "2026-11-13"
REMOVE = ["wpxf9f34d9f44"]

wp = json.load(open("wallpapers.json"))
removed = set()
for cat, lst in wp["categories"].items():
    keep = []
    for e in lst:
        if e["id"] in REMOVE:
            for p in (f"{cat}/{e['id']}.jpg", f"{cat}/{e['id']}_thumb.jpg"):
                if os.path.exists(p):
                    os.remove(p)
            removed.add(e["id"])
            print("removed", cat, e["id"], flush=True)
        else:
            keep.append(e)
    wp["categories"][cat] = keep

added = json.load(open("_tmp/n2/added.json"))
final = [x for x in added if x[1] not in removed]
json.dump(final, open("_tmp/n2/added.json", "w"), indent=1)
wp["version"] = int(wp.get("version", 0)) + 1
wp["last_updated"] = DATE
with open("wallpapers.json", "w", encoding="utf-8") as f:
    json.dump(wp, f, ensure_ascii=False, separators=(",", ":"))
print("FINAL", len(final), "version", wp["version"], flush=True)

for p in ["_tmp/night2_run.py", "_tmp/night2_fix.py",
          "_tmp/night2_picks.json", "_tmp/night2_series.txt",
          "_tmp/night2_fetch.py", ".tmp-write-test.txt"]:
    if os.path.exists(p):
        os.remove(p)
        print("cleaned", p, flush=True)
if os.path.isdir("_tmp/n2"):
    shutil.rmtree("_tmp/n2")
    print("cleaned _tmp/n2", flush=True)
