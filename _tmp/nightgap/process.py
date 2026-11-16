import json, os, random, re
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
MAN = json.load(open(os.path.join(HERE, "manifest.json")))
SEL = json.load(open(os.path.join(HERE, "selection.json")))
DATE = "2026-11-16"

SHOW_TAGS = {
    "monogatari": ["monogatari", "monogatari series", "bakemonogatari", "nadeko", "shinobu"],
    "bakemono": ["bakemonogatari", "monogatari", "monogatari series", "hitagi"],
    "gundam": ["gundam", "mobile suit gundam", "mecha", "mobile suit"],
    "gintama": ["gintama", "gintoki", "samurai", "odd jobs"],
    "kuroko": ["kuroko", "kuroko no basket", "kuroko's basketball", "basketball"],
    "digimon": ["digimon", "digimon adventure", "digital monster"],
    "eightsix": ["86", "86 eighty six", "eighty six", "lena", "spearhead squadron"],
    "dorohedoro": ["dorohedoro", "caiman", "nikaido"],
    "champloo": ["samurai champloo", "mugen", "jin", "fuu"],
    "yurionice": ["yuri on ice", "yuri!!! on ice", "yuuri", "victor"],
    "higurashi": ["higurashi", "higurashi no naku koro ni", "when they cry"],
    "elfenlied": ["elfen lied", "lucy", "nyu"],
    "gantz": ["gantz", "kurono", "kei"],
    "dororo": ["dororo", "hyakkimaru"],
    "flcl": ["flcl", "fooly cooly", "haruko"],
    "slamdunk": ["slam dunk", "hanamichi", "sakuragi", "basketball"],
    "skip": ["skip and loafer", "skip to loafer", "mitsumi"],
    "medalist": ["medalist", "inori", "figure skating"],
    "towerofgod": ["tower of god", "kami no tou", "bam", "rachel"],
    "undead": ["undead unluck", "andy", "fuuko"],
}

META = set("""highres absurdres huge_filesize very_highres lowres redo recent oldest year
solo solo_focus multiple_girls multiple_boys 1girl 1boy 2girls 2boys 3girls 4girls
anime scan translated english_text comment request commentary
anime_wallpaper wallpaper phone_wallpaper portrait wallpaper_pack
mobile_wallpaper smartphone_wallpaper""".split())

MOOD = {
    "night": ["night", "starry_sky", "moon", "dark"],
    "rain": ["rain", "rainy", "wet"],
    "city": ["city", "cityscape", "urban", "building", "skyline", "neon"],
    "sky": ["sky", "cloud", "sunset", "sunrise", "blue_sky", "space"],
    "dark": ["dark", "black", "shadow", "silhouette", "amoled"],
    "cute": ["smile", "blush", "cute", "happy"],
    "sad": ["crying", "tears", "sad"],
    "action": ["sword", "weapon", "beam_saber", "fighting", "battle", "explosion"],
    "water": ["water", "ocean", "sea", "river", "underwater"],
    "flower": ["flower", "flowers", "cherry_blossoms", "petals", "red_flower"],
    "snow": ["snow", "winter", "snowing"],
    "autumn": ["autumn", "leaves", "fall"],
    "school": ["school_uniform", "uniform", "classroom", "school"],
}

COLOR = ["white_hair", "black_hair", "blonde_hair", "brown_hair", "red_hair", "pink_hair",
         "blue_hair", "purple_hair", "green_hair", "silver_hair", "grey_hair", "orange_hair",
         "red_eyes", "blue_eyes", "green_eyes", "yellow_eyes", "purple_eyes", "golden_eyes"]


def clean(t):
    t = t.replace("\\", "").replace("(", "").replace(")", "")
    return re.sub(r"\s+", " ", t.replace("_", " ")).strip().lower()


def build_tags(item, show):
    raw = [t for t in item["tags"].split() if t not in META]
    out = list(SHOW_TAGS.get(show, [show]))
    for c in COLOR:
        if c in raw:
            out.append(clean(c))
    for mood, keys in MOOD.items():
        if any(k in raw for k in keys):
            out.append(mood)
    for t in raw:
        if len(out) >= 15:
            break
        if t.startswith("year_") or len(t) > 24:
            continue
        out.append(clean(t))
    seen, final = set(), []
    for t in out:
        if not t or t in seen or len(t) < 2:
            continue
        seen.add(t)
        final.append(t)
    for extra in ["anime", "aesthetic", "portrait wallpaper", "phone wallpaper"]:
        if len(final) >= 10:
            break
        if extra not in seen:
            final.append(extra)
            seen.add(extra)
    return ",".join(final[:15])


def fit(src, dst, size):
    im = Image.open(src).convert("RGB")
    w, h = im.size
    target = size[0] / size[1]
    if w / h > target:
        nw = int(h * target)
        left = (w - nw) // 2
        im = im.crop((left, 0, left + nw, h))
    else:
        nh = int(w / target)
        top = max(0, int((h - nh) * 0.3))
        im = im.crop((0, top, w, top + nh))
    im = im.resize(size, Image.LANCZOS)
    im.save(dst, "JPEG", quality=95, optimize=True)


def main():
    wp_path = os.path.join(ROOT, "wallpapers.json")
    data = json.load(open(wp_path))
    added = []
    for pick in SEL:
        show = pick["show"]
        pid = pick["id"]
        src = os.path.join(HERE, "cand", show, "%s.jpg" % pid)
        if not os.path.exists(src):
            print("missing", src)
            continue
        item = None
        for it in MAN.get(show, {}).get("items", []):
            if str(it["id"]) == str(pid):
                item = it
                break
        if item is None:
            print("no manifest entry", show, pid)
            continue
        cat = pick["cat"]
        wid = "wpx" + "".join(random.choice("0123456789abcdef") for _ in range(10))
        folder = os.path.join(ROOT, cat)
        os.makedirs(folder, exist_ok=True)
        fit(src, os.path.join(folder, wid + ".jpg"), (1080, 1920))
        fit(src, os.path.join(folder, wid + "_thumb.jpg"), (360, 640))
        base = "https://raw.githubusercontent.com/nobelfamily537-dev/AniPix-Walls/main/%s/" % cat
        entry = {"id": wid, "thumb": base + wid + "_thumb.jpg",
                 "full": base + wid + ".jpg", "alt": base + wid + ".jpg",
                 "tags": build_tags(item, show), "date": DATE}
        data["categories"][cat].insert(0, entry)
        added.append((cat, wid, show, pid, entry["tags"]))
    data["version"] = int(data.get("version", 0)) + 1
    data["last_updated"] = DATE
    with open(wp_path, "w") as f:
        json.dump(data, f, ensure_ascii=False)
    print("added", len(added))
    for a in added:
        print(a[0], a[1], a[2], a[3])
        print("   tags:", a[4])


main()
