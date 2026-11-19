#!/usr/bin/env python3
"""Build picks.json for lowrun19 from reviewed candidate indices (danbooru e*/f* dirs)."""
import json, os, re

OUT = "_tmp/lowrun19"
DIRS = ["e0", "e1", "e2", "f0", "f1", "f2"]

cands = {}
for d in DIRS:
    p = os.path.join(OUT, d, "cands.json")
    if not os.path.exists(p):
        continue
    for c in json.load(open(p)):
        cands["%s:%s:%s" % (d, c["slug"], c["idx"])] = c

# series exact tag (as in wallpapers.json tag index), alt form, category
SERIES = {
    "the-apothecary-diaries": ("the apothecary diaries", "kusuriya no hitorigoto"),
    "the-promised-neverland": ("the promised neverland", "yakusoku no neverland"),
    "a-certain-scientific-railgun": ("a certain scientific railgun", "toaru kagaku no railgun"),
    "mashle": ("mashle", "mashle magic and muscles"),
    "horimiya": ("horimiya", "hori-san to miyamura-kun"),
    "fire-force": ("fire force", "enen no shouboutai"),
    "erased": ("erased", "boku dake ga inai machi"),
    "porco-rosso": ("porco rosso", "kurenai no buta"),
    "god-eater": ("god eater", None),
    "the-cat-returns": ("the cat returns", "neko no ongaeshi"),
    "vinland-saga": ("vinland saga", None),
    "the-wind-rises": ("the wind rises", "kaze tachinu"),
    "ponyo": ("ponyo", "gake no ue no ponyo"),
    "from-up-on-poppy-hill": ("from up on poppy hill", "kokuriko-zaka kara"),
}

PLAN = {
    "the-apothecary-diaries": ("e2", [0, 1, 3, 4, 5, 7, 8, 9, 10, 11, 13, 14, 15, 17, 18]),
    "the-promised-neverland": ("e0", [0, 1, 2, 3, 4, 8, 10, 11, 12, 13, 15, 17, 18]),
    "a-certain-scientific-railgun": ("e0", [0, 1, 3, 5, 6, 7, 9, 10, 11, 13, 14, 15, 16, 17, 19]),
    "mashle": ("f0", [1, 2, 3, 4, 5, 7, 8, 9, 11, 13, 15, 16, 17]),
    "horimiya": ("f1", [2, 4, 6, 7, 8, 10, 16, 18]),
    "fire-force": ("e0", [1, 4, 5, 7, 10, 11, 12]),
    "erased": ("e1", [0, 1, 5, 8, 9, 10, 13, 14]),
    "porco-rosso": ("e2", [1, 2, 6]),
    "god-eater": ("e1", [0, 2, 3, 5]),
    "the-cat-returns": ("f1", [2, 3, 4]),
    "vinland-saga": ("f2", [0, 1, 2, 5]),
    "the-wind-rises": ("e1", [0, 1, 2, 3, 6]),
    "ponyo": ("f1", [4]),
    "from-up-on-poppy-hill": ("e2", [1]),
}
EXTRA = {"horimiya": [("e1", 0), ("e1", 1)]}

META = {"highres", "absurdres", "incredibly_absurdres", "huge_filesize", "lowres", "1girl", "1boy",
        "2girls", "2boys", "3girls", "multiple_girls", "multiple_boys", "solo", "solo_focus",
        "looking_at_viewer", "alternate_costume", "alternate_hairstyle", "official_art", "commentary",
        "translated", "artist_name", "watermark", "signature", "text", "english_text", "bad_id",
        "bad_pixiv_id", "bad_twitter_id", "twitter_username", "web_address", "dated", "scenery",
        "no_humans", "simple_background", "white_background", "black_background", "gradient_background",
        "resolution_mismatch", "md5_mismatch", "revision", "variant_set", "sample", "scan", "tagme",
        "commentary_request", "translation_request", "character_request", "artist_request", "absurdres",
        "grey_background", "two-tone_background", "border", "photo", "3d", "realistic", "depth_of_field",
        "blurry", "blurry_foreground", "blurry_background", "cowboy_shot", "upper_body", "lower_body",
        "portrait", "close-up", "full_body", "standing", "sitting", "smile", "open_mouth", "blush"}


def clean(t):
    t = t.replace("_", " ").strip().lower()
    t = re.sub(r"\(.*?\)", "", t).strip()
    return t


picks = []
for slug, (d, idxs) in PLAN.items():
    tag, alt = SERIES[slug]
    items = [(d, i) for i in idxs] + EXTRA.get(slug, [])
    for k, (dd, i) in enumerate(items):
        c = cands.get("%s:%s:%s" % (dd, slug, i))
        if not c:
            print("MISSING", slug, dd, i)
            continue
        tags = []
        for t in [tag, alt]:
            if t and t not in tags:
                tags.append(t)
        for t in [clean(x) for x in c.get("chars", "").split()] + \
                 [clean(x) for x in c.get("gen", "").split()]:
            if not t or t in META or len(t) < 2 or t in tags:
                continue
            tags.append(t)
        tags = tags[:15]
        cat = "anime" if k % 2 == 0 else "anime2"
        picks.append(dict(series=tag, slug=slug, idx=i, src="%s:%s" % (dd, i), pid=c["pid"],
                          url=c["url"], tags=tags, cat=cat))

# dedupe by url
seen, out = set(), []
for p in picks:
    if p["url"] in seen:
        print("DUP URL dropped", p["slug"], p["src"])
        continue
    seen.add(p["url"])
    out.append(p)
json.dump(out, open(os.path.join(OUT, "picks.json"), "w"), indent=1)
print("picks", len(out))
from collections import Counter
c = Counter(p["series"] for p in out)
for k, v in c.most_common():
    print("  %-32s %d" % (k, v))
print("cat split", Counter(p["cat"] for p in out))
