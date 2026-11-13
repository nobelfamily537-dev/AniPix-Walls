#!/usr/bin/env python3
"""Final tag polish for short entries + cleanup of staging files."""
import json, os, shutil, subprocess

FIX = {
 "wpx57edf82315": "closeup,red hair,dark,melancholy",
 "wpx2c90de5fbf": "military uniform,purple hair,cape",
 "wpx9f379ec43e": "sitting,white background,long hair,school uniform",
 "wpx1927a9a127": "sitting,school uniform,long hair,indoor",
 "wpxa80ced4933": "triangle frame,city,night",
 "wpxb24053a14d": "closeup,white background,melancholy",
 "wpx086a752b86": "melancholy,short hair,90s anime",
 "wpx2b8a2c056e": "sword,duelist,portrait",
 "wpx670be295e7": "orange,sword,duelist",
 "wpx03f85f3d19": "school uniform,pink hair,sitting",
 "wpxbb01c7e327": "long hair,school uniform,portrait",
 "wpx407dad8307": "two characters,school uniform,red",
 "wpxf3af4696e9": "triangle frame,city,night",
 "wpxb7c2dcdab3": "fire,embers,cloak,orange",
 "wpxb9bbd16d6c": "flame,glow,dark,portrait",
 "wpxfa8a128d4c": "armor,blade,warrior",
 "wpx4a3637ca0c": "flame,cloak,dark",
 "wpx251ea36e78": "closeup,long hair,glow",
 "wpx485bb75078": "maid outfit,purple,dark",
 "wpxa052e213dd": "pink hair,room,books,portrait",
 "wpxad857998d6": "purple,crystal,fantasy",
 "wpx50d7074b50": "white hair,lying,portrait",
 "wpx9781c963a5": "green,flowers,dark,android",
 "wpx81aa064347": "white background,portrait,android",
}
BAD = {"scenery", "vertical", "portrait", "phone wallpaper", "anime art"}

wp = json.load(open("wallpapers.json"))
tags_idx = wp.setdefault("tags", {})
ents = {}
for cat, items in wp["categories"].items():
    for e in items:
        ents[e["id"]] = e

for i, extra in FIX.items():
    e = ents.get(i)
    if not e:
        print("missing", i)
        continue
    cur = [t.strip() for t in e["tags"].split(",") if t.strip()]
    cur = [t for t in cur if t not in BAD]
    for t in [x.strip() for x in extra.split(",") if x.strip()]:
        if t not in cur:
            cur.append(t)
    if len(cur) < 10:
        for t in ("portrait", "anime art"):
            if len(cur) >= 10:
                break
            if t not in cur:
                cur.append(t)
    e["tags"] = ",".join(cur[:15])
    for t in cur:
        lst = tags_idx.setdefault(t, [])
        if i not in lst:
            lst.append(i)

# drop index refs for tags removed from these entries
for t, lst in list(tags_idx.items()):
    lst2 = [x for x in lst if not (x in FIX and t not in [y.strip() for y in ents[x]["tags"].split(",")])]
    if lst2:
        tags_idx[t] = lst2
    else:
        del tags_idx[t]

json.dump(wp, open("wallpapers.json", "w"), ensure_ascii=False, separators=(",", ":"))

# cleanup staging
for p in ("_tmp/lc/stage", "_tmp/lc/sheets"):
    if os.path.isdir(p):
        shutil.rmtree(p, ignore_errors=True)
for p in ("_tmp/lc/manifest.json", "_tmp/lc/approved.json", "_tmp/lc/tagfix.json",
          "_tmp/lc/probe.txt", "_tmp/lc/trigger-fetch.txt", "_tmp/lc/trigger-publish.txt",
          "_tmp/lc/trigger-tagfix.txt", "_tmp/lc/trigger-rebuild.txt", "_tmp/lc/trigger-final.txt",
          "_tmp/lc/fetch.py", "_tmp/lc/publish.py", "_tmp/lc/enrich.py", "_tmp/lc/tagfix.py",
          "_tmp/lc/rebuild.py", "_tmp/lc/final.py"):
    if os.path.exists(p):
        subprocess.run(["git", "rm", "-q", "-f", p], check=False)
for p in (".github/workflows/_tmp-lc-fetch.yml", ".github/workflows/_tmp-lc-publish.yml",
          ".github/workflows/_tmp-lc-tagfix.yml", ".github/workflows/_tmp-lc-rebuild.yml",
          ".github/workflows/_tmp-lc-final.yml"):
    if os.path.exists(p):
        subprocess.run(["git", "rm", "-q", "-f", p], check=False)
print("done")
