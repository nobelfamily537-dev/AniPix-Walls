#!/usr/bin/env python3
"""Build picks.json drafts: map chosen indices -> rich tags (run locally in sandbox)."""
import colorsys, json, os, re, sys
from PIL import Image

OUT = "_tmp/lowrun21"
cands = json.load(open(os.path.join(OUT, "cands.json")))
by_key = {(c["series"], c["idx"]): c for c in cands}

# series key -> (alt common form, extra series aliases for tags)
ALT = {
    "a silent voice": ["koe no katachi", "shouko nishimiya", "shouya ishida"],
    "akatsuki no yona": ["yona of the dawn", "yona", "hak"],
    "food wars": ["shokugeki no soma", "souma yukihira", "megumi tadokoro"],
    "the cat returns": ["neko no ongaeshi", "baron humbert von gikkingen", "haru"],
    "chihayafuru": ["chihaya ayase", "karuta", "taichi mashima"],
    "ponyo": ["gake no ue no ponyo", "sosuke", "fujimoto"],
    "porco rosso": ["kurenai no buta", "marco pagot", "fio piccolo"],
    "kill la kill": ["ryuuko matoi", "satsuki kiryuin", "senketsu", "mako mankanshoku"],
    "the wind rises": ["kaze tachinu", "jiro horikoshi", "naoko satomi"],
    "oregairu": ["yahari ore no seishun love comedy wa machigatteiru", "yukino yukinoshita",
                 "yui yuigahama", "hachiman hikigaya", "my teen romantic comedy snafu"],
    "bubble": ["utai", "hibiki"],
    "vinland saga": ["thorfinn", "askeladd", "canute"],
    "seven deadly sins": ["nanatsu no taizai", "meliodas", "elizabeth liones", "escanor"],
    "rurouni kenshin": ["samurai x", "kenshin himura", "kaoru kamiya"],
    "noragami": ["yato", "hiori ikishima", "yukine"],
    "fire force": ["enen no shouboutai", "shinra kusakabe", "tamaki kotatsu"],
}

# booru tag -> kept?  useful visual/character descriptors
KEEP_WORDS = {
    "long_hair", "short_hair", "very_long_hair", "black_hair", "white_hair", "silver_hair", "blonde",
    "blonde_hair", "brown_hair", "red_hair", "pink_hair", "blue_hair", "purple_hair", "orange_hair",
    "green_hair", "grey_hair", "twintails", "ponytail", "braids", "bun", "hair_bun", "hime_cut",
    "blue_eyes", "red_eyes", "green_eyes", "golden_eyes", "purple_eyes", "pink_eyes", "aqua_eyes",
    "heterochromia", "closed_eyes", "one_eye_closed", "eyepatch", "blindfold",
    "sword", "katana", "holding_sword", "bow", "arrow", "staff", "shield", "armor", "armour",
    "kimono", "yukata", "hakama", "school_uniform", "serafuku", "sailor_collar", "blazer", "hoodie",
    "jacket", "coat", "cloak", "cape", "dress", "skirt", "pleated_skirt", "shorts", "scarf",
    "hat", "cap", "ribbon", "hair_ribbon", "hairband", "gloves", "boots", "sneakers", "sandals",
    "night", "night_sky", "starry_sky", "full_moon", "moon", "sunset", "sunrise", "dusk", "dawn",
    "clouds", "cloudy_sky", "blue_sky", "sky", "rain", "snow", "fog", "mist", "storm", "lightning",
    "cherry_blossoms", "sakura", "petals", "flowers", "flower_field", "sunflower", "autumn_leaves",
    "forest", "tree", "trees", "grass", "field", "mountain", "mountains", "ocean", "sea", "beach",
    "river", "lake", "waterfall", "city", "cityscape", "city_lights", "buildings", "street",
    "rooftop", "school", "classroom", "shrine", "torii", "temple", "castle", "ruins", "window",
    "indoors", "outdoors", "scenery", "landscape", "silhouette", "backlighting", "lens_flare",
    "wind", "floating", "flying", "standing", "sitting", "walking", "looking_at_viewer",
    "from_behind", "from_side", "profile", "upper_body", "full_body", "cowboy_shot", "portrait",
    "smile", "smiling", "grin", "laughing", "calm", "serious", "confident", "determined", "proud",
    "peaceful", "melancholy", "sad", "nostalgic", "dreamy", "ethereal", "romantic", "warm",
    "animal", "cat", "dog", "bird", "birds", "fish", "butterfly", "dragon", "wolf", "horse",
    "feathers", "wings", "angels", "umbrella", "lantern", "lanterns", "festival", "fireworks",
    "book", "books", "violin", "piano", "guitar", "headphones", "phone", "cup", "teacup",
    "japanese_clothes", "traditional", "military", "uniform", "fantasy", "magic", "glowing",
    "fire", "water", "ice", "smoke", "sparks", "particles", "bokeh", "depth_of_field",
}
DROP_SUB = ("_(cosplay)",)

CHAR_STOP = {
    "1girl", "2girls", "3girls", "1boy", "2boys", "multiple_girls", "multiple_boys", "solo",
    "male", "female", "animal", "no_humans", "chibi",
}


def colour_theme(path):
    im = Image.open(path).convert("RGB").resize((48, 84))
    px = list(im.getdata())
    buckets = {"red": 0.0, "orange": 0.0, "yellow": 0.0, "green": 0.0, "teal": 0.0,
               "blue": 0.0, "purple": 0.0, "pink": 0.0}
    for r, g, b in px:
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if s < 0.14 or v < 0.13:
            continue
        deg = h * 360
        if deg < 15 or deg >= 345:
            k = "red"
        elif deg < 40:
            k = "orange"
        elif deg < 68:
            k = "yellow"
        elif deg < 155:
            k = "green"
        elif deg < 190:
            k = "teal"
        elif deg < 255:
            k = "blue"
        elif deg < 300:
            k = "purple"
        else:
            k = "pink"
        buckets[k] += s * v
    if not any(buckets.values()):
        return "dark theme"
    best = max(buckets, key=buckets.get)
    total = sum(buckets.values())
    share = buckets[best] / total
    if share < 0.26:
        return "colorful"
    return best + " theme"


def char_tags(tags):
    out = []
    for t in tags.split():
        if t in CHAR_STOP:
            continue
        if re.match(r"^[a-z0-9_]+_\([a-z0-9_:.\-]+\)$", t):  # character_(series)
            nm = t.split("_(")[0].replace("_", " ").strip()
            if nm and len(nm) > 2:
                out.append(nm)
        elif "_(" in t:
            continue
    return out


def visual_tags(tags):
    out = []
    for t in tags.split():
        if t in KEEP_WORDS:
            out.append(t.replace("_", " "))
    return out


def build(sel):
    """sel: list of (series, idx, cat, focus/fx overrides dict)"""
    picks = []
    for item in sel:
        series, idx, cat = item[0], item[1], item[2]
        opts = item[3] if len(item) > 3 else {}
        c = by_key.get((series, idx))
        if not c:
            print("MISSING", series, idx)
            continue
        alt = ALT.get(series, [])
        tags = [series]
        if alt:
            tags.append(alt[0])
        tags += char_tags(c["tags"])[:4]
        vt = visual_tags(c["tags"])
        tags += vt[:8]
        tags.append(colour_theme(os.path.join(OUT, "prev", c["file"])))
        tags.append("aesthetic")
        seen, fin = set(), []
        for t in tags:
            t = t.strip().lower()
            if not t or t in seen:
                continue
            seen.add(t)
            fin.append(t)
        fin = fin[:15]
        p = dict(series=series, name=c["name"], slug=c["slug"], idx=idx, pid=c["pid"], site=c["site"],
                 w=c["w"], h=c["h"], url=c["url"], cat=cat, tags=fin)
        p.update(opts)
        picks.append(p)
    return picks


if __name__ == "__main__":
    sel = json.load(open(sys.argv[1]))
    picks = build(sel)
    json.dump(picks, open(sys.argv[2], "w"), indent=1)
    for p in picks:
        print(p["series"], p["idx"], p["cat"], "|", ",".join(p["tags"]))
