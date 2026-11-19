#!/usr/bin/env python3
"""Build picks.json for lowrun19 from reviewed candidate indices."""
import json, os, re, sys

OUT = "_tmp/lowrun19"
cands = json.load(open(os.path.join(OUT, "cands.json")))
by = {}
for c in cands:
    by.setdefault(c["slug"], {})[c["idx"]] = c

# slug -> (exact index tag, alt form or None, picks: [idx...], cat)
PLAN = json.load(open(os.path.join(OUT, "plan.json")))

META = {"highres", "absurdres", "incredibly_absurdres", "huge_filesize", "lowres", "1girl", "1boy",
        "2girls", "2boys", "3girls", "multiple_girls", "multiple_boys", "solo", "solo_focus",
        "looking_at_viewer", "alternate_costume", "alternate_hairstyle", "official_art", "commentary",
        "translated", "artist_name", "watermark", "signature", "text", "english_text", "bad_id",
        "bad_pixiv_id", "bad_twitter_id", "twitter_username", "web_address", "dated", "scenery",
        "no_humans", "simple_background", "white_background", "black_background", "gradient_background",
        "resolution_mismatch", "md5_mismatch", "revision", "variant_set", "sample", "scan",
        "tagme", "commentary_request", "translation_request", "character_request", "artist_request"}


def clean(t):
    t = t.replace("_", " ").strip().lower()
    t = re.sub(r"\(.*?\)", "", t).strip()
    return t


picks = []
for slug, cfg in PLAN.items():
    items = by.get(slug, {})
    for idx in cfg["picks"]:
        c = items.get(idx)
        if not c:
            print("MISSING", slug, idx)
            continue
        tags = []
        for t in [cfg["tag"], cfg.get("alt")] + [clean(x) for x in c["tags"].split()]:
            if not t:
                continue
            t = t.strip().lower()
            if not t or t in META or len(t) < 2:
                continue
            if t not in tags:
                tags.append(t)
        tags = tags[:15]
        picks.append(dict(series=cfg["tag"], slug=slug, idx=idx, pid=c["pid"], site=c["site"],
                          url=c["url"], tags=tags, cat=cfg.get("cat", "anime")))
json.dump(picks, open(os.path.join(OUT, "picks.json"), "w"), indent=1)
print("picks", len(picks))
from collections import Counter
print(Counter(p["series"] for p in picks))
