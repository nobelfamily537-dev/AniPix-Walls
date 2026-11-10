#!/usr/bin/env python3
"""Cleanup: drop rejected wallpapers, fix tags, remove staging files."""
import json, os, shutil

BAD = ["wpa417d909f7", "wpce7d40858b", "wpccaf1a408b", "wpb91c0d2be6"]

data = json.load(open("wallpapers.json", encoding="utf-8"))

removed = []
for cat, items in data["categories"].items():
    keep = []
    for e in items:
        if e["id"] in BAD:
            removed.append((e["id"], cat))
            for suf in ("", "_thumb"):
                p = "%s/%s%s.jpg" % (cat, e["id"], suf)
                if os.path.exists(p):
                    os.remove(p)
            continue
        keep.append(e)
    data["categories"][cat] = keep

for t in list(data["tags"].keys()):
    ids = [i for i in data["tags"][t] if i not in BAD]
    if ids:
        data["tags"][t] = ids
    else:
        del data["tags"][t]

# Clannad entry: the character is Ushio, not Nagisa
for e in data["categories"]["anime2"]:
    if e["id"] == "wpa2a9c0efc2":
        e["tags"] = e["tags"].replace("nagisa furukawa", "ushio okazaki")

json.dump(data, open("wallpapers.json", "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))

if os.path.isdir("_stage"):
    shutil.rmtree("_stage", ignore_errors=True)
wf = ".github/workflows/lowcount-probe.yml"
if os.path.exists(wf):
    os.remove(wf)

today = [e for c in data["categories"].values() for e in c if e.get("date") == "2026-11-10"]
print("removed", removed)
print("remaining dated today", len(today))
