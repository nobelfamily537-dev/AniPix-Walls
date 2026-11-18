#!/usr/bin/env python3
"""Delete rejected low21 wallpapers (files only) and remove temp run assets."""
import json, os, subprocess

drop = json.load(open("_tmp/low21/drop.json"))
files = []
for wid, cat in drop.items():
    for suffix in (".jpg", "_thumb.jpg"):
        p = "%s/%s%s" % (cat, wid, suffix)
        if os.path.exists(p):
            files.append(p)
print("deleting", len(files), "files")
if files:
    subprocess.run(["git", "rm", "-q", "--sparse"] + files, check=False)
    for p in files:
        if os.path.exists(p):
            os.remove(p)
print("done files")
