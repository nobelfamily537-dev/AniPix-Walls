#!/usr/bin/env python3
"""Low-count run v22: process reviewed picks into the repo."""
import os, io, json, time, hashlib
import requests
from PIL import Image

OUT = "_tmp/lowrun22"
TODAY = "2026-11-21"
REPO = "nobelfamily537-dev/AniPix-Walls"
RAW = "https://raw.githubusercontent.com/%s/main" % REPO
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

EXTRA = {
    "natsume yuujinchou": ["natsume yuujinchou", "natsume's book of friends", "natsume takashi", "nyanko sensei"],
    "seraph of the end": ["seraph of the end", "owari no seraph", "shinoa hiiragi", "hyakuya mikaela", "yuichiro hyakuya"],
    "k-on": ["k-on", "k-on!", "hokago tea time", "hirasawa yui", "akiyama mio"],
    "nisekoi": ["nisekoi", "nisekoi false love", "kirisaki chitoge", "onodera kosaki"],
    "blue exorcist": ["blue exorcist", "ao no exorcist", "okumura rin", "okumura yukio"],
    "a silent voice": ["a silent voice", "koe no katachi", "nishimiya shouko", "ishida shouya"],
    "yona of the dawn": ["yona of the dawn", "akatsuki no yona", "yona", "son hak", "shin-ah"],
}
DROP = {"1girl", "1boy", "2girls", "2boys", "solo", "male_focus", "multiple_girls", "multiple_boys",
        "highres", "absurdres", "commentary", "commentary_request", "bad_id", "artist_request",
        "official_art", "transparent_background", "alternate_costume", "variant_set",
        "large_filesize", "third-party_edit", "edit", "twitter_username", "web_address", "censored",
        "scan", "sample", "text", "english_text", "watermark", "signature", "artist_name", "logo"}

data = json.load(open("wallpapers.json", encoding="utf-8"))
known = set(data["tags"].keys())
cands = {}
for cf in ("cand3", "cand7", "cand9"):
    for c in json.load(open(os.path.join(OUT, cf + ".json"))):
        pre = {"cand3": "w", "cand7": "s", "cand9": "g"}[cf]
        cands["%s%02d" % (pre, c["idx"])] = c
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


def build_tags(c, tag):
    out = list(EXTRA.get(tag, [tag]))
    raw = [t.replace("_", " ") for t in (c.get("tags") or "").split()]
    for t in raw:
        if len(out) >= 13:
            break
        if t in DROP or len(t) < 3 or t in out:
            continue
        if t in known:
            out.append(t)
    for t in ("anime wallpaper", "phone wallpaper"):
        if t not in out and len(out) < 15:
            out.append(t)
    return out


added, skipped = {}, []
n = 0
for p in picks:
    c = cands.get(p["label"])
    if not c:
        skipped.append((p["series"], p["label"], "no candidate"))
        continue
    try:
        r = requests.get(c["url"], headers=dict(UA, Referer="https://%s/" % c["site"]), timeout=90)
        r.raise_for_status()
        im = Image.open(io.BytesIO(r.content))
        im.load()
        im = im.convert("RGB")
    except Exception as e:
        skipped.append((p["series"], p["label"], "download " + type(e).__name__))
        continue
    if im.width < 700 or im.height < 900:
        skipped.append((p["series"], p["label"], "small %dx%d" % im.size))
        continue
    im2 = crop_916(im).resize((1080, 1920), Image.LANCZOS)
    cat = p["category"]
    os.makedirs(cat, exist_ok=True)
    wid = new_id()
    im2.save(os.path.join(cat, wid + ".jpg"), "JPEG", quality=95, optimize=True, progressive=True)
    im2.resize((360, 640), Image.LANCZOS).save(os.path.join(cat, wid + "_thumb.jpg"), "JPEG", quality=80, optimize=True)
    entry = {
        "id": wid,
        "thumb": "%s/%s/%s_thumb.jpg" % (RAW, cat, wid),
        "full": "%s/%s/%s.jpg" % (RAW, cat, wid),
        "alt": "%s/%s/%s.jpg" % (RAW, cat, wid),
        "tags": ",".join(build_tags(c, p["tag"])),
        "date": TODAY,
    }
    data["categories"].setdefault(cat, []).append(entry)
    for t in entry["tags"].split(","):
        data["tags"].setdefault(t, []).append(wid)
    added[p["series"]] = added.get(p["series"], 0) + 1
    n += 1
    time.sleep(0.1)

data["version"] = int(data.get("version", 99)) + 1
data["last_updated"] = TODAY
json.dump(data, open("wallpapers.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
json.dump({"added": added, "skipped": skipped, "total": n}, open(os.path.join(OUT, "result.json"), "w"), indent=1)
print("ADDED:", json.dumps(added), "total", n, flush=True)
print("SKIPPED:", json.dumps(skipped), flush=True)
