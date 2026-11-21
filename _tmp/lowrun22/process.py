#!/usr/bin/env python3
"""Low-count run v22: process the reviewed picks into wallpapers.json."""
import os, io, json, time, random, hashlib
import requests
from PIL import Image

OUT = "_tmp/lowrun22"
TODAY = "2026-11-21"
REPO = "nobelfamily537-dev/AniPix-Walls"
RAW = "https://raw.githubusercontent.com/%s/main" % REPO
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

# app series tag -> extra tags appended to every wallpaper of that series
EXTRA = {
    "quintessential quintuplets": ["gotoubun no hanayome", "the quintessential quintuplets", "nakano quintuplets"],
    "a silent voice": ["koe no katachi", "shouko nishimiya", "shoya ishida"],
    "food wars": ["shokugeki no soma", "yukihira souma", "totsuki"],
    "natsume yuujinchou": ["natsume's book of friends", "natsume takashi", "nyanko sensei"],
    "yona of the dawn": ["akatsuki no yona", "yona", "son hak"],
    "oregairu": ["yahari ore no seishun", "my teen romantic comedy snafu", "hachiman hikigaya", "yukino yukinoshita"],
    "the wind rises": ["kaze tachinu", "studio ghibli", "naoko satomi", "jirou horikoshi"],
    "jigokuraku": ["hell's paradise", "jigokuraku hell's paradise", "gabimaru", "sagiri"],
    "kuroko no basket": ["kuroko's basketball", "kuroko tetsuya", "seirin"],
    "fire force": ["enen no shouboutai", "shinra kusakabe", "special fire force"],
}

DROP = {"1girl", "1boy", "2girls", "2boys", "solo", "male_focus", "multiple_girls", "multiple_boys",
        "highres", "absurdres", "commentary", "commentary_request", "bad_id", "bad_pixiv_id",
        "artist_request", "official_art", "transparent_background", "alternate_costume",
        "alternate_hairstyle", "variant_set", "duplicate", "resolution", "absurdres_request",
        "large_filesize", "third-party_edit", "edit", "twitter_username", "web_address"}

data = json.load(open("wallpapers.json", encoding="utf-8"))
known = set(data["tags"].keys())
cands = {c["name"]: c for c in json.load(open(os.path.join(OUT, "cand.json")))}
picks = json.load(open(os.path.join(OUT, "picks.json")))

existing_ids = {e["id"] for arr in data["categories"].values() for e in arr}


def new_id():
    while True:
        i = "wpx" + hashlib.md5(os.urandom(16)).hexdigest()[:10]
        if i not in existing_ids:
            existing_ids.add(i)
            return i


def crop_916(im):
    w, h = im.size
    t = 9 / 16
    if w / h > t:
        nw = int(h * t)
        x = (w - nw) // 2
        return im.crop((x, 0, x + nw, h))
    nh = int(w / t)
    y = int((h - nh) * 0.35)
    return im.crop((0, y, w, y + nh))


def build_tags(c):
    raw = [t.replace("_", " ") for t in (c["tags"] or "").split()]
    out = []
    for t in EXTRA[c["series"]]:
        out.append(t)
    for t in raw:
        if t in DROP or len(t) < 3 or len(out) >= 15:
            continue
        if t in known and t not in out:
            out.append(t)
    for t in ("anime wallpaper", "phone wallpaper"):
        if t not in out and len(out) < 15:
            out.append(t)
    return out


added = {}
fail = []
picks_sorted = sorted(picks, key=lambda p: (p["series"], p["name"]))
n = 0
for p in picks_sorted:
    c = cands.get(p["name"])
    if not c:
        fail.append((p["name"], "no candidate"))
        continue
    try:
        r = requests.get(c["url"], headers=UA, timeout=90)
        r.raise_for_status()
        im = Image.open(io.BytesIO(r.content))
        im.load()
        im = im.convert("RGB")
    except Exception as e:
        fail.append((p["name"], "download %s" % type(e).__name__))
        continue
    if im.width < 800 or im.height < 1100:
        fail.append((p["name"], "too small %dx%d" % im.size))
        continue
    im = crop_916(im).resize((1080, 1920), Image.LANCZOS)
    cat = p.get("category") or ("anime" if n % 2 == 0 else "anime2")
    os.makedirs(cat, exist_ok=True)
    wid = new_id()
    im.save(os.path.join(cat, wid + ".jpg"), "JPEG", quality=95, optimize=True, progressive=True)
    im.resize((360, 640), Image.LANCZOS).save(os.path.join(cat, wid + "_thumb.jpg"), "JPEG", quality=80, optimize=True)
    entry = {
        "id": wid,
        "thumb": "%s/%s/%s_thumb.jpg" % (RAW, cat, wid),
        "full": "%s/%s/%s.jpg" % (RAW, cat, wid),
        "alt": "%s/%s/%s.jpg" % (RAW, cat, wid),
        "tags": ",".join(build_tags(c)),
        "date": TODAY,
    }
    data["categories"].setdefault(cat, []).append(entry)
    for t in entry["tags"].split(","):
        data["tags"].setdefault(t, []).append(wid)
    added.setdefault(c["series"], 0)
    added[c["series"]] += 1
    n += 1
    time.sleep(0.2)

data["version"] = int(data.get("version", 99)) + 1
data["last_updated"] = TODAY
json.dump(data, open("wallpapers.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
json.dump({"added": added, "fail": fail, "total": n}, open(os.path.join(OUT, "result.json"), "w"), indent=1)
print("added:", added, "total", n)
print("fail:", fail)
