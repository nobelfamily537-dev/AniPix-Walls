#!/usr/bin/env python3
"""Drop off-series/low-quality picks and rebuild tags for the 2026-11-13 batch."""
import json, os, re, hashlib, subprocess

DROP_IDS = [
    "wpx3f1d906066", "wpx1bc687b19c", "wpxe3003422a3", "wpx820abd7e31",
    "wpxf00b8f12d7", "wpx63537eaa51", "wpxc9e9eecb92", "wpxc74d1c1164",
]

wp = json.load(open("wallpapers.json"))
tags_idx = wp.setdefault("tags", {})
approved = json.load(open("_tmp/lc/approved.json"))

def wid(slug, key):
    return "wpx" + hashlib.sha1(f"{slug}:{key}".encode()).hexdigest()[:10]

meta = {wid(i["slug"], i["key"]): i for i in approved["items"]}

# ---- remove entries + files ----
removed = set()
for cat, items in wp["categories"].items():
    keep = []
    for e in items:
        if e["id"] in DROP_IDS:
            removed.add(e["id"])
            for ext in (".jpg", "_thumb.jpg"):
                p = os.path.join(cat, e["id"] + ext)
                if os.path.exists(p):
                    subprocess.run(["git", "rm", "-q", "-f", p], check=False)
        else:
            keep.append(e)
    wp["categories"][cat] = keep
for t, lst in list(tags_idx.items()):
    lst2 = [i for i in lst if i not in removed]
    if lst2:
        tags_idx[t] = lst2
    else:
        del tags_idx[t]
print("removed", len(removed))

# ---- rebuild tags for the new batch ----
JUNK = {"commentary request", "copyright name", "1other", "?", "question mark", "absurdres",
        "highres", "artist request", "official art", "game cg", "photo (medium)", "cosplay photo",
        "commentary", "translated", "english commentary", "edit", "watermarked", "sample",
        "pixiv", "deviantart", "4k", "ultrawide", "portrait display", "simple background",
        "digital media (artwork)", "illustration", "artwork", "digital art", "video game art",
        "video games", "video game characters", "video game girls", "anime", "anime girls",
        "anime boys", "anime games", "anime style", "fan art", "women", "men", "group of women",
        "women outdoors", "multiple characters", "anime wallpaper", "1girl", "1boy", "solo",
        "solo focus", "male focus", "looking at viewer", "mihoyo", "copyright", "chinese", "kanji",
        "big boobs", "guns", "girls with guns", "gun", "weapon", "weapons", "holding weapon"}

def clean(t):
    t = t.replace("_", " ").strip().lower()
    t = re.sub(r"\([^)]*\)$", "", t).strip()
    t = re.sub(r"\s+", " ", t)
    return t

def colour_of(colors):
    for c in colors[:3]:
        hx = c.lstrip("#").lower()
        try:
            r, g, b = int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)
        except Exception:
            continue
        mx, mn = max(r, g, b), min(r, g, b)
        if mx < 60: return "black"
        if mn > 190: return "white"
        if mx - mn < 30: return "grey"
        if r >= g and r >= b: return "red" if g < 110 else ("orange" if g < 175 else "yellow")
        if g >= r and g >= b: return "green" if r < 130 else "teal"
        if b >= r and b >= g:
            return "blue" if r < 120 else ("purple" if r > 140 and g < 130 else "blue")
    return ""

changed = 0
for cat, items in wp["categories"].items():
    for e in items:
        if e.get("date") != "2026-11-13":
            continue
        m = meta.get(e["id"])
        if not m:
            continue
        out = []

        def add(x):
            x = clean(x)
            if not x or len(x) < 3 or len(x) > 32:
                return
            if x in JUNK or x in out:
                return
            out.append(x)

        add(m.get("series_tag", ""))
        if m.get("alt_series"):
            add(m["alt_series"])
        for t in m.get("src_tags", []):
            add(t)
        col = colour_of(m.get("colors") or [])
        if col:
            add(col)
        src = " ".join(m.get("src_tags", [])).lower()
        fillers = ["portrait", "scenery", "fan art", "digital art", "illustration", "anime art",
                   "phone wallpaper", "vertical"]
        if "scenery" in src or "outdoors" in src or "sky" in src or "landscape" in src:
            fillers = ["scenery"] + [f for f in fillers if f != "scenery"]
        for f in fillers:
            if len(out) >= 11:
                break
            add(f)
        add("anime wallpaper")
        e["tags"] = ",".join(out[:15])
        changed += 1

# rebuild index refs for new batch
for cat, items in wp["categories"].items():
    for e in items:
        if e.get("date") != "2026-11-13":
            continue
        for t in [x.strip() for x in e["tags"].split(",") if x.strip()]:
            lst = tags_idx.setdefault(t, [])
            if e["id"] not in lst:
                lst.append(e["id"])

json.dump(wp, open("wallpapers.json", "w"), ensure_ascii=False, separators=(",", ":"))
print("retagged", changed)
