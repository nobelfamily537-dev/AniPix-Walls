#!/usr/bin/env python3
"""Final QA pass: drop wallpapers with visible text/watermarks, top up thin tag
lists, and remove the temp scaffolding used for this run."""
import json, os, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
TODAY = "2026-11-12"

REMOVE = {
    "wpxa4a41fc5e4": "visible script signature",
    "wpx5e916fd0d1": "printed title text in art",
    "wpx9b3f2624dc": "illust watermark bottom right",
    "wpxfdffb7d52d": "instagram/artstation signature",
    "wpx9745a94f16": "signature mark bottom left",
    "wpx6e469bb2fe": "oversized mirrored logo",
    "wpx6ff43de853": "oversized mirrored logo",
    "wpx215ea88719": "mostly black, unreadable",
    "wpxc4cf29961e": "unflattering crop",
    "wpxd00903965b": "unrecognisable abstract crop",
    "wpx5c33ccf104": "artist signature",
    "wpxac1469626a": "printed series title text",
    "wpx0b20e59e83": "printed text across image",
    "wpxbb363d6308": "artist signature",
    "wpx5b30136d36": "artist signature",
}

wj = json.load(open(os.path.join(ROOT, "wallpapers.json"), encoding="utf-8"))
cats = wj["categories"]
tags_idx = wj["tags"]

found = {}
for cat, lst in cats.items():
    keep = []
    for e in lst:
        if e["id"] in REMOVE:
            found[e["id"]] = cat
        else:
            keep.append(e)
    cats[cat] = keep
print("removed entries:", len(found), "of", len(REMOVE))
missing = set(REMOVE) - set(found)
if missing:
    print("NOT FOUND:", missing)

for t, ids in list(tags_idx.items()):
    if any(i in REMOVE for i in ids):
        tags_idx[t] = [i for i in ids if i not in REMOVE]

# delete image files
for wid, cat in found.items():
    for suffix in (".jpg", "_thumb.jpg"):
        p = os.path.join(ROOT, cat, wid + suffix)
        if os.path.exists(p):
            os.remove(p)
        else:
            print("missing file", p)

# top up tag lists to at least 10 keywords
POOL_ANIME = ["anime wallpaper", "phone wallpaper", "anime art", "digital art", "portrait"]
POOL_GAME = ["game wallpaper", "anime style", "digital art", "portrait", "character art"]
fixed = 0
for cat, lst in cats.items():
    pool = POOL_GAME if cat == "game" else POOL_ANIME
    for e in lst:
        if e.get("date") != TODAY:
            continue
        tl = [t.strip() for t in e["tags"].split(",") if t.strip()]
        if len(tl) >= 10:
            continue
        for extra in pool:
            if len(tl) >= 10:
                break
            if extra not in tl:
                tl.append(extra)
        e["tags"] = ",".join(tl[:15])
        for t in tl:
            tags_idx.setdefault(t, [])
            if e["id"] not in tags_idx[t]:
                tags_idx[t].insert(0, e["id"])
        fixed += 1
print("tag lists topped up:", fixed)

json.dump(wj, open(os.path.join(ROOT, "wallpapers.json"), "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))

# remove this run's scaffolding
for name in ("fetch_low.py", "process_low.py", "series.json", "series2.json",
             "candidates.json", "candidates2.json", "picks.json",
             "trigger_low.txt", "trigger_low2.txt", "trigger_process.txt",
             "trigger_fix.txt", "fix_low.py"):
    p = os.path.join(HERE, name)
    if os.path.exists(p):
        os.remove(p)
for d in ("cand", "cand2", "sheets", "sheets2"):
    shutil.rmtree(os.path.join(HERE, d), ignore_errors=True)
for wf in ("_tmp-low-fetch.yml", "_tmp-low-fetch2.yml", "_tmp-low-process.yml",
           "_tmp-low-fix.yml"):
    p = os.path.join(ROOT, ".github", "workflows", wf)
    if os.path.exists(p):
        os.remove(p)
print("cleanup done")
