#!/usr/bin/env python3
"""Build picks.json for the low20 run from cands.json + a selection map."""
import json, colorsys, os
from PIL import Image

OUT = "_tmp/low20"

# slug -> list of candidate idx values chosen from the contact sheets
SELECTION = json.load(open(os.path.join(OUT, "selection.json")))

# priority buckets of descriptive tags (konachan underscore form)
BUCKET = [
    # scene / setting
    ["night_sky", "starry_sky", "stars", "night", "full_moon", "crescent_moon", "moon", "sunset",
     "sunrise", "dawn", "dusk", "twilight", "golden_hour", "cloud", "clouds", "blue_sky", "sky",
     "rain", "snow", "winter", "spring", "summer", "autumn", "ocean", "sea", "beach", "lake",
     "river", "waterfall", "mountain", "mountains", "forest", "tree", "trees", "field", "meadow",
     "grass", "city", "cityscape", "skyline", "street", "neon_lights", "lights", "window", "rooftop",
     "room", "indoors", "outdoors", "ruins", "castle", "temple", "shrine", "torii", "stairs",
     "bridge", "train", "school", "classroom", "festival", "lantern", "lanterns", "fireworks",
     "sparkle", "light_rays", "glow", "magic", "aura", "flames", "fire", "lightning", "smoke",
     "mist", "fog", "floating", "silhouette", "reflection", "water_reflection", "scenery",
     "landscape", "fantasy", "sci-fi", "futuristic", "mecha", "dragon", "butterfly", "jellyfish",
     "whale", "planet", "space", "nebula", "galaxy"],
    # objects / props
    ["sword", "katana", "dagger", "spear", "bow", "staff", "shield", "wings", "feathers", "mask",
     "umbrella", "book", "flowers", "cherry_blossoms", "petals", "rose", "roses", "sunflowers",
     "sakura", "leaf", "autumn_leaves", "ribbon", "hat", "witch_hat", "cape", "scarf", "gloves"],
    # clothing
    ["school_uniform", "sailor_collar", "kimono", "yukata", "hakama", "hoodie", "jacket", "coat",
     "cloak", "armor", "dress", "suit", "neck_tie", "boots", "thighhighs", "maid", "serafuku",
     "traditional_clothes", "japanese_clothes", "hanfu", "uniform"],
    # appearance
    ["long_hair", "short_hair", "blonde_hair", "black_hair", "white_hair", "silver_hair", "red_hair",
     "blue_hair", "pink_hair", "purple_hair", "brown_hair", "green_hair", "orange_hair", "grey_hair",
     "twintails", "ponytail", "braids", "hair_ornament", "hair_ribbon", "blue_eyes", "red_eyes",
     "green_eyes", "golden_eyes", "purple_eyes", "heterochromia", "closed_eyes", "looking_at_viewer",
     "looking_away", "side_profile", "smile", "serious", "blush", "tears", "portrait", "close-up",
     "full_body", "upper_body", "back_view", "from_behind", "profile", "standing", "sitting",
     "walking", "dynamic_pose", "action"],
    # mood / style
    ["cinematic", "dramatic", "epic", "serene", "peaceful", "calm", "melancholic", "nostalgic",
     "dreamy", "ethereal", "vibrant", "moody", "dark", "atmospheric", "painterly", "detailed",
     "highly_detailed", "soft_lighting", "warm_light", "cool_tones", "pastel", "aesthetic",
     "romantic", "powerful", "intense", "quiet", "lonely", "whimsical", "surreal", "gothic",
     "retro", "cyberpunk"],
]

META = {"1girl", "2girls", "1boy", "2boys", "solo", "solo_focus", "multiple_girls", "multiple_boys",
        "highres", "absurdres", "huge_filesize", "incredibly_absurdres", "commentary", "translated",
        "english_text", "text", "watermark", "signature", "artist_name", "dated", "twitter_username",
        "web_address", "logo", "border", "scan", "sample", "variant_set", "bad_pixiv_id", "no_humans",
        "official_art", "game_cg", "wallpaper", "phone_wallpaper", "wide_image", "key_visual",
        "promotional_art", "poster", "banner", "album", "cover", "character_request", "artist_request",
        "revision", "md5_mismatch", "resolution_mismatch", "bad_twitter_id", "bad_link", "check_translation"}


def colour_theme(path):
    im = Image.open(path).convert("RGB").resize((60, 106))
    px = list(im.getdata())
    best = {}
    for r, g, b in px:
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if s < 0.12 or v < 0.10:
            continue
        deg = h * 360
        if deg < 15 or deg >= 345:
            n = "red"
        elif deg < 40:
            n = "orange"
        elif deg < 68:
            n = "gold"
        elif deg < 160:
            n = "green"
        elif deg < 200:
            n = "teal"
        elif deg < 250:
            n = "blue"
        elif deg < 290:
            n = "purple"
        elif deg < 320:
            n = "magenta"
        else:
            n = "pink"
        best[n] = best.get(n, 0) + (s * v)
    if not best:
        return None
    top = max(best.items(), key=lambda kv: kv[1])[0]
    return "%s theme" % top


def build(c):
    tags = []
    itag = c["itag"]
    alt = c.get("alt")
    cand_tags = set(c["tags"].split())
    chars = []
    for ch in c.get("chars") or []:
        if ch.replace(" ", "_") in cand_tags:
            chars.append(ch)
    desc = []
    for bucket in BUCKET:
        for t in bucket:
            if t in cand_tags and t.replace("_", " ") not in desc:
                desc.append(t.replace("_", " "))
    colour = colour_theme(os.path.join(OUT, "prev2", c["file"]))
    order = [itag]
    if alt and alt != itag:
        order.append(alt)
    order += chars[:3]
    order += desc[:9]
    if colour:
        order.append(colour)
    for pad in ("anime wallpaper", "phone wallpaper", "detailed art", "cinematic"):
        if len(order) >= 11:
            break
        order.append(pad)
    out = []
    for x in order:
        x = x.strip().lower()
        if x and x not in out:
            out.append(x)
    return out[:15]


import sys
CANDS = sys.argv[1] if len(sys.argv) > 1 else "cands2.json"
cands = json.load(open(os.path.join(OUT, CANDS)))
by_slug = {}
for c in cands:
    by_slug.setdefault(c["slug"], {})[c["idx"]] = c

picks = []
missing = []
for slug, idxs in SELECTION.items():
    for i in idxs:
        c = by_slug.get(slug, {}).get(i)
        if not c:
            missing.append((slug, i))
            continue
        tags = build(c)
        picks.append(dict(series=c["series"], slug=slug, idx=i, pid=c["pid"], site=c["site"],
                          url=c["url"], cat=c["cat"], tags=tags))

json.dump(picks, open(os.path.join(OUT, "picks.json"), "w"), indent=1)
print("picks:", len(picks), "missing:", missing)
from collections import Counter
print(Counter(p["series"] for p in picks))
print("cat:", Counter(p["cat"] for p in picks))
for p in picks[:3]:
    print(p["series"], p["tags"])
