import json, os, random, re, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
MAN = json.load(open(os.path.join(HERE, "manifest.json")))
SEL = json.load(open(os.path.join(HERE, "selection.json")))

SHOW_TAGS = {
    "monogatari": ["monogatari", "monogatari series", "bakemonogatari", "senjougahara", "araragi"],
    "gundam": ["gundam", "mobile suit gundam", "mecha", "mobile suit"],
    "gintama": ["gintama", "gintoki", "odd jobs", "samurai"],
    "kuroko": ["kuroko", "kuroko no basket", "kuroko's basketball", "basketball"],
    "digimon": ["digimon", "digimon adventure", "digital monster"],
    "eightsix": ["86", "86 eighty six", "eighty six", "lena", "shin"],
    "dorohedoro": ["dorohedoro", "caiman", "nikaido"],
    "champloo": ["samurai champloo", "mugen", "jin", "fuu"],
    "yurionice": ["yuri on ice", "yuri!!! on ice", "yuuri", "victor"],
}

META = set("""highres absurdres huge_filesize very_highres lowres redo recent oldest year
solo solo_focus multiple_girls multiple_boys 1girl 1boy 2girls 2boys 3girls 4girls 6+girls
general sensitive questionable explicit bad_score good_score great_score aesthetic
masterpiece best_quality very_aesthetic normal_quality displeasing bad_quality
commentary_request commentary request english_commentary translated
variations alternate_costume alternate_hairstyle absurdres""".split())

MOOD = {
    "night": ["night", "starry_sky", "moon", "dark"],
    "rain": ["rain", "rainy", "wet"],
    "city": ["city", "cityscape", "urban", "building", "skyline", "neon"],
    "sky": ["sky", "cloud", "sunset", "sunrise", "blue_sky"],
    "dark": ["dark", "black", "shadow", "silhouette", "amoled"],
    "cute": ["smile", "blush", "cute", "happy"],
    "sad": ["crying", "tears", "sad"],
    "action": ["sword", "weapon", "fighting", "battle", "action", "beam_saber"],
    "water": ["water", "ocean", "sea", "river", "underwater"],
    "flower": ["flower", "flowers", "cherry_blossoms", "petals"],
    "snow": ["snow", "winter", "snowing"],
    "autumn": ["autumn", "leaves", "fall"],
    "school": ["school_uniform", "uniform", "classroom", "school"],
}

COLOR = ["white_hair", "black_hair", "blonde_hair", "brown_hair", "red_hair", "pink_hair",
         "blue_hair", "purple_hair", "green_hair", "silver_hair", "grey_hair", "orange_hair",
         "red_eyes", "blue_eyes", "green_eyes", "yellow_eyes", "purple_eyes", "golden_eyes"]


def clean(t):
    t = t.replace("\\", "").replace("(", "").replace(")", "").strip()
    return t.replace("_", " ")


def build_tags(item, show):
    raw = [t for t in item["tags"].split() if t not in META]
    out = []
    out += SHOW_TAGS.get(show, [show])
    for c in COLOR:
        if c in raw:
            out.append(clean(c))
    for mood, keys in MOOD.items():
        if any(k in raw for k in keys):
            out.append(mood)
    for t in raw:
        if len(out) >= 15:
            break
        if t.startswith(("year_", "dated")) or len(t) > 26:
            continue
        out.append(clean(t))
    seen, final = set(), []
    for t in out:
        t = re.sub(r"\s+", " ", t).strip().lower()
        if not t or t in seen or len(t) < 2:
            continue
        seen.add(t)
        final.append(t)
    while len(final) < 10:
        for extra in ["anime", "aesthetic", "portrait wallpaper", "phone wallpaper", "art"]:
            if extra not in seen:
                final.append(extra); seen.add(extra)
            if len(final) >= 10:
                break
    return ",".join(final[:15])


def process(src, dst, size):
    im = Image.open(src).convert("RGB")
    w, h = im.size
    target = size[0] / size[1]
    if w / h > target:
        nw = int(h * target)
        left = (w - nw) // 2
        im = im.crop((left, 0, left + nw, h))
    else:
        nh = int(w / target)
        top = max(0, int((h - nh) * 0.35))
        im = im.crop((0, top, w, top + nh))
    im = im.resize(size, Image.LANCZOS)
    im.save(dst, "JPEG", quality=95, optimize=True)


def main():
    wp_path = os.path.join(ROOT, "wallpapers.json")
    data = json.load(open(wp_path))
    existing = set()
    for cat in data["categories"].values():
        for w in cat:
            existing.add(w.get("full", ""))
    added = []
    for i, pick in enumerate(SEL):
        show = pick["show"]
        n = pick["n"]
        items = MAN[show]["items"]
        item = next((x for x in items if x["n"] == n), None)
        if item is None:
            print("skip missing", show, n)
            continue
        cat = pick.get("cat") or ("anime" if i % 2 == 0 else "anime2")
        wid = "wpx" + "".join(random.choice("0123456789abcdef") for _ in range(10))
        folder = os.path.join(ROOT, cat)
        os.makedirs(folder, exist_ok=True)
        full_name = wid + ".jpg"
        thumb_name = wid + "_thumb.jpg"
        process(item["file"], os.path.join(folder, full_name), (1080, 1920))
        process(item["file"], os.path.join(folder, thumb_name), (360, 640))
        base = "https://raw.githubusercontent.com/nobelfamily537-dev/AniPix-Walls/main/%s/" % cat
        entry = {
            "id": wid,
            "thumb": base + thumb_name,
            "full": base + full_name,
            "alt": base + full_name,
            "tags": build_tags(item, show),
            "date": "2026-11-16",
        }
        data["categories"][cat].insert(0, entry)
        added.append((cat, wid, MAN[show]["name"]))
    data["version"] = int(data.get("version", 0)) + 1
    data["last_updated"] = "2026-11-16"
    json.dump(data, open(wp_path, "w"), ensure_ascii=False)
    print("added", len(added))
    for a in added:
        print(a)


main()
