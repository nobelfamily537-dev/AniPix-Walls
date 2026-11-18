#!/usr/bin/env python3
"""Low-count run (2026-11-18): stage 3 - enrich tags on today's entries."""
import json, hashlib, subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

TODAY = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
OUT = "_tmp/low20"
NAME, MAIL = "AniPix Bot", "nobelfamily537@gmail.com"

DESC = [
    ("white_hair", "white hair"), ("silver_hair", "silver hair"), ("black_hair", "black hair"),
    ("brown_hair", "brown hair"), ("blonde_hair", "blonde hair"), ("green_hair", "green hair"),
    ("red_hair", "red hair"), ("purple_hair", "purple hair"), ("orange_hair", "orange hair"),
    ("long_hair", "long hair"), ("short_hair", "short hair"), ("twintails", "twintails"),
    ("ponytail", "ponytail"), ("braid", "braid"), ("hair_ribbon", "hair ribbon"),
    ("hairband", "hairband"), ("hair_ornament", "hair ornament"), ("ahoge", "ahoge"),
    ("blue_eyes", "blue eyes"), ("green_eyes", "green eyes"), ("red_eyes", "red eyes"),
    ("yellow_eyes", "yellow eyes"), ("purple_eyes", "purple eyes"), ("brown_eyes", "brown eyes"),
    ("heterochromia", "heterochromia"), ("glasses", "glasses"),
    ("school_uniform", "school uniform"), ("serafuku", "sailor uniform"), ("blazer", "blazer"),
    ("hoodie", "hoodie"), ("coat", "coat"), ("jacket", "jacket"), ("dress", "dress"),
    ("black_dress", "black dress"), ("lace", "lace"), ("veil", "veil"), ("kimono", "kimono"),
    ("yukata", "yukata"), ("qipao", "qipao"), ("maid", "maid outfit"), ("apron", "apron"),
    ("scarf", "scarf"), ("gloves", "gloves"), ("hat", "hat"), ("beret", "beret"),
    ("headphones", "headphones"), ("earrings", "earrings"), ("choker", "choker"),
    ("jewelry", "jewelry"), ("necktie", "necktie"), ("sweater", "sweater"), ("skirt", "skirt"),
    ("pleated_skirt", "pleated skirt"), ("boots", "boots"), ("thighhighs", "thigh highs"),
    ("sword", "sword"), ("katana", "katana"), ("gun", "gun"), ("staff", "staff"),
    ("guitar", "guitar"), ("bass_guitar", "bass guitar"), ("drums", "drums"), ("microphone", "microphone"),
    ("sitting", "sitting"), ("standing", "standing"), ("lying", "lying down"),
    ("looking_at_viewer", "looking at viewer"), ("looking_away", "looking away"),
    ("from_side", "side profile"), ("profile", "profile"), ("upper_body", "upper body"),
    ("full_body", "full body"), ("portrait", "portrait"), ("solo", "solo"),
    ("smile", "smile"), ("closed_eyes", "closed eyes"), ("blush", "blush"),
    ("night", "night"), ("moon", "moon"), ("stars", "starry sky"), ("sky", "sky"),
    ("clouds", "clouds"), ("sunset", "sunset"), ("dusk", "dusk"), ("rain", "rain"),
    ("snow", "snow"), ("city", "city"), ("cityscape", "cityscape"), ("building", "buildings"),
    ("window", "window"), ("indoors", "indoors"), ("outdoors", "outdoors"),
    ("cherry_blossoms", "cherry blossoms"), ("flowers", "flowers"), ("wisteria", "wisteria"),
    ("autumn", "autumn"), ("summer", "summer"), ("winter", "winter"), ("spring", "spring"),
    ("ocean", "ocean"), ("beach", "beach"), ("forest", "forest"), ("mountain", "mountains"),
    ("water", "water"), ("river", "river"), ("street", "street"), ("lantern", "lanterns"),
    ("neon_lights", "neon"), ("lights", "lights"), ("backlighting", "backlighting"),
    ("blurry", "soft focus"), ("depth_of_field", "depth of field"), ("monochrome", "monochrome"),
    ("watercolor", "watercolor"), ("traditional_media", "traditional art"), ("copic", "marker art"),
    ("silhouette", "silhouette"), ("wind", "wind"), ("cat", "cat"), ("dog", "dog"),
    ("wings", "wings"), ("armor", "armor"), ("mecha", "mecha"), ("vehicle", "vehicle"),
    ("books", "books"), ("food", "food"), ("umbrella", "umbrella"), ("festival", "festival"),
    ("fireworks", "fireworks"), ("couple", "couple"), ("two_shot", "two shot"),
]

data = json.load(open("wallpapers.json", encoding="utf-8"))
cands = json.load(open(OUT + "/cands.json"))
bywid = {}
for c in cands:
    bywid["wpx" + hashlib.sha1(c["url"].encode()).hexdigest()[:10]] = c

changed = 0
for cat in ("anime", "anime2", "game", "nature"):
    for e in data["categories"].get(cat, []):
        if e.get("date") != TODAY:
            continue
        c = bywid.get(e["id"])
        if not c:
            continue
        old = [t for t in e["tags"].split(",") if t]
        series = old[0]
        raw = set((c.get("tags") or "").split())
        tags = [series]
        if c.get("alt") and c["alt"].lower() != series.lower():
            tags.append(c["alt"])
        for cr in (c.get("copyr") or "").split()[:2]:
            nm = cr.replace("_", " ")
            if nm.lower() != series.lower():
                tags.append(nm)
        n = 0
        for ch in (c.get("chars") or "").split():
            if n >= 3:
                break
            tags.append(ch.replace("_", " ").strip())
            n += 1
        for key, label in DESC:
            if key in raw:
                tags.append(label)
        theme = [t for t in old if t.endswith(" theme")]
        tags += theme[:1]
        out, seen = [], set()
        for x in tags:
            x = " ".join(x.lower().split())
            if x and x not in seen:
                seen.add(x)
                out.append(x)
        out = out[:15]
        for filler in ("anime wallpaper", "phone wallpaper", "portrait art", "anime art"):
            if len(out) >= 10:
                break
            if filler not in seen:
                out.append(filler)
                seen.add(filler)
        if out == old:
            continue
        for t in old:
            if t not in out and e["id"] in data["tags"].get(t, []):
                data["tags"][t].remove(e["id"])
        for t in out:
            data["tags"].setdefault(t, [])
            if e["id"] not in data["tags"][t]:
                data["tags"][t].insert(0, e["id"])
        e["tags"] = ",".join(out)
        changed += 1

json.dump(data, open("wallpapers.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("retagged", changed, flush=True)
subprocess.run(["git", "add", "-A"], check=True)
subprocess.run(["git", "-c", "user.name=" + NAME, "-c", "user.email=" + MAIL,
                "commit", "-m", "Enrich tags on %s low-count batch (%d entries)" % (TODAY, changed)], check=True)
subprocess.run(["git", "pull", "--rebase", "--autostash"], check=True)
subprocess.run(["git", "push"], check=True)
print("PUSHED tags", flush=True)
