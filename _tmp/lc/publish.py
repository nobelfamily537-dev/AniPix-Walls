#!/usr/bin/env python3
"""Publish approved low-count candidates into categories + wallpapers.json."""
import os, json, re, hashlib, shutil, datetime

ROOT = "_tmp/lc"
STAGE = f"{ROOT}/stage"
DATE = datetime.datetime.utcnow().astimezone(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d")

appr = json.load(open(f"{ROOT}/approved.json"))
DATE = appr.get("date", DATE)
wp = json.load(open("wallpapers.json"))
cats = wp["categories"]
tags_idx = wp.setdefault("tags", {})

existing_ids = {e["id"] for items in cats.values() for e in items}
existing_urls = set()
for items in cats.values():
    for e in items:
        for f in (e.get("full"), e.get("thumb"), e.get("alt")):
            if f:
                existing_urls.add(f)

RAW = "https://raw.githubusercontent.com/nobelfamily537-dev/AniPix-Walls/main"

DROP = {
    "1girl", "1boy", "solo", "hires", "highres", "absurdres", "commentary", "commentary_request",
    "translated", "english_commentary", "looking_at_viewer", "simple_background", "white_background",
    "alternate_costume", "official_art", "artist_name", "signature", "watermark", "text", "logo",
    "multiple_views", "character_sheet", "bad_id", "bad_pixiv_id", "bad_twitter_id", "web_address",
    "dated", "twitter_username", "english_text", "artist_logo", "censor", "censored", "uncensored",
    "ass", "nude", "naked", "topless", "cleavage", "large_breasts", "huge_breasts", "bikini",
    "swimsuit", "underwear", "panties", "bra", "see_through", "spread_legs", "bed", "loli",
}
GENERIC = {"anime", "anime style", "fan art", "digital media (artwork)", "illustration",
           "artist request", "game cg", "official art", "konachan", "pixiv", "danbooru"}

def norm(t):
    t = t.replace("_", " ").strip().lower()
    t = re.sub(r"\([^)]*\)$", "", t).strip()
    t = re.sub(r"\s+", " ", t)
    return t

def build_tags(item, series_tag, src_tags, colors):
    out = []
    def add(x):
        x = x.strip().lower()
        if not x or len(x) < 3 or len(x) > 32:
            return
        if x in DROP or x in GENERIC or x in out:
            return
        out.append(x)
    add(series_tag)
    for t in src_tags:
        raw = t.strip()
        if raw.lower().replace("_", " ") in DROP:
            continue
        add(norm(raw))
    if colors:
        hexes = [c.lstrip("#").lower() for c in colors[:3]]
        for hx in hexes:
            try:
                r, g, b = int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)
            except Exception:
                continue
            mx, mn = max(r, g, b), min(r, g, b)
            if mx < 60:
                name = "black"
            elif mn > 190:
                name = "white"
            elif mx - mn < 30:
                name = "grey"
            elif r >= g and r >= b:
                name = "red" if g < 110 else ("orange" if g < 175 else "yellow")
            elif g >= r and g >= b:
                name = "green" if r < 130 else "teal"
            else:
                name = "blue" if r < 120 else ("purple" if r > 140 and g < 120 else "blue")
            add(name)
            break
    add("anime wallpaper")
    return ",".join(out[:15])

stats = {}
used = 0
for it in appr["items"]:
    slug, key, cat = it["slug"], it["key"], it["category"]
    src = os.path.join(STAGE, slug, f"{key}.jpg")
    th = os.path.join(STAGE, slug, f"{key}_thumb.jpg")
    if not (os.path.exists(src) and os.path.exists(th)):
        print("MISSING", slug, key)
        continue
    seed = f"{slug}:{key}"
    wid = "wpx" + hashlib.sha1(seed.encode()).hexdigest()[:10]
    n = 0
    while wid in existing_ids:
        n += 1
        wid = "wpx" + hashlib.sha1((seed + str(n)).encode()).hexdigest()[:10]
    os.makedirs(cat, exist_ok=True)
    shutil.copyfile(src, os.path.join(cat, f"{wid}.jpg"))
    shutil.copyfile(th, os.path.join(cat, f"{wid}_thumb.jpg"))
    series_tag = it.get("series_tag") or ""
    if it.get("tags"):
        tagstr = it["tags"]
    else:
        tagstr = build_tags(it, series_tag, it.get("src_tags", []), it.get("colors", []))
    url = f"{RAW}/{cat}/{wid}.jpg"
    entry = {
        "id": wid,
        "thumb": f"{RAW}/{cat}/{wid}_thumb.jpg",
        "full": url,
        "alt": url,
        "tags": tagstr,
        "date": DATE,
    }
    cats[cat].append(entry)
    existing_ids.add(wid)
    existing_urls.update([entry["full"], entry["thumb"]])
    for t in [x.strip() for x in tagstr.split(",") if x.strip()]:
        tags_idx.setdefault(t, [])
        if wid not in tags_idx[t]:
            tags_idx[t].append(wid)
    stats[slug] = stats.get(slug, 0) + 1
    used += 1

wp["version"] = int(wp.get("version", 0)) + 1
wp["last_updated"] = DATE
json.dump(wp, open("wallpapers.json", "w"), ensure_ascii=False, separators=(",", ":"))
print("added", used)
for k, v in stats.items():
    print(f"  {k}: {v}")
