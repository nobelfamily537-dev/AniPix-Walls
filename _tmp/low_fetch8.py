#!/usr/bin/env python3
"""Low-count run v8: wallhaven candidates for the 10 emptiest series."""
import os, io, json, time, re
import requests
from PIL import Image, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

SERIES = [
    ("initial d", ["initial d", "ae86", "toyota sprinter trueno", "takumi fujiwara"]),
    ("pokemon", ["pokemon", "pikachu", "pokemon trainer", "gengar"]),
    ("detective conan", ["detective conan", "conan edogawa", "ran mouri", "case closed"]),
    ("clannad", ["clannad", "nagisa furukawa", "tomoyo sakagami"]),
    ("dragon ball super", ["dragon ball super", "goku ultra instinct", "vegeta super saiyan"]),
    ("neon genesis evangelion", ["evangelion", "asuka langley", "rei ayanami", "eva unit 01"]),
    ("konosuba", ["konosuba", "megumin", "aqua konosuba", "darkness konosuba"]),
    ("seven deadly sins", ["seven deadly sins", "meliodas", "escanor", "elizabeth liones"]),
    ("nausicaa", ["nausicaa", "nausicaa of the valley of the wind"]),
    ("berserk", ["berserk", "guts berserk", "griffith berserk"]),
    ("howls moving castle", ["howl's moving castle", "howl pendragon"]),
    ("kaiju no 8", ["kaiju no 8", "kaiju no. 8", "kafka hibino"]),
]

BAD = {"text", "english_text", "watermark", "signature", "artist_name", "speech_bubble", "comic", "4koma",
       "multiple_views", "character_sheet", "translated", "logo", "border", "frame", "letterboxed",
       "twitter_username", "web_address", "dated", "artist_logo", "english_commentary", "bad_id",
       "sketch", "monochrome", "greyscale", "partially_colored", "gun", "mecha", "vehicle", "blood",
       "gore", "censored", "manga", "scan", "sample", "food", "chibi", "comic_panel", "bikini",
       "swimsuit", "underwear", "lingerie", "panties", "bra", "cleavage", "no_bra", "see_through",
       "cameltoe", "spread_legs", "large_breasts", "huge_breasts", "ass", "nude", "naked", "topless",
       "wet", "bed", "bottomless", "sideboob", "underboob", "photo", "photograph", "cosplay",
       "screencap", "screenshot", "reference_sheet", "concept_art", "upscaled", "jpeg_artifacts", "lowres"}

OUT = "_tmp/prevlow8"
os.makedirs(OUT, exist_ok=True)
cands = []


def render(im, size=(360, 640)):
    w, h = im.size
    r = h / w
    tw, th = size
    t = 9 / 16
    if r > 2.05:
        bg = ImageOps.fit(im, (tw, th), method=Image.LANCZOS).filter(ImageFilter.GaussianBlur(22))
        fg = im.copy()
        fg.thumbnail((tw, th), Image.LANCZOS)
        bg.paste(fg, ((tw - fg.width) // 2, (th - fg.height) // 2))
        return bg
    if r > t:
        nh = int(w / t)
        y = int((h - nh) * (0.04 if r >= 1.55 else 0.18))
        return im.crop((0, y, w, y + nh))
    nw = int(h * t)
    x = (w - nw) // 2
    return im.crop((x, 0, x + nw, h))


def get(url, params, timeout=20):
    for attempt in range(2):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout)
            if r.status_code == 200:
                time.sleep(1.1)
                return r
            print("  HTTP", r.status_code, flush=True)
        except Exception as e:
            print("  ERR", type(e).__name__, flush=True)
        time.sleep(2)
    return None


def wallhaven(q):
    out = []
    for page in (1, 2):
        r = get("https://wallhaven.cc/api/v1/search",
                {"q": q, "categories": "010", "purity": "100", "atleast": "1080x1500",
                 "sorting": "favorites", "page": page})
        if not r:
            break
        try:
            js = r.json()
        except Exception:
            break
        for d in js.get("data", []):
            out.append(dict(src="wallhaven", id=d["id"], score=(d.get("favorites") or 0),
                            w=d["dimension_x"], h=d["dimension_y"], url=d["path"],
                            prev=(d.get("thumbs") or {}).get("large") or d["path"],
                            md5=d["id"], tags=" ".join(t["name"] for t in d.get("tags", []))))
        if js.get("meta", {}).get("current_page", 1) >= js.get("meta", {}).get("last_page", 1):
            break
    return out


def ok(p):
    if not p["url"] or not p["w"] or not p["h"]:
        return False
    r = p["h"] / p["w"]
    if r >= 1.25:
        if p["h"] < 1400:
            return False
    elif r <= 0.7:
        if p["w"] < 1800:
            return False
    else:
        return False
    if set(p["tags"].split()) & BAD:
        return False
    return True


for name, wqs in SERIES:
    pool = []
    for q in wqs:
        pool += wallhaven(q)
    print("== %s: pool=%d" % (name, len(pool)), flush=True)
    seen, kept = set(), []
    pool.sort(key=lambda p: -(p["score"] or 0))
    for p in pool:
        key = p["md5"]
        if key in seen:
            continue
        seen.add(key)
        if ok(p):
            kept.append(p)
    print("   valid=%d" % len(kept), flush=True)

    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    n = 0
    for p in kept:
        if n >= 22:
            break
        try:
            r = requests.get(p["prev"], headers=UA, timeout=20)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            fn = "%s_%02d.jpg" % (slug, n)
            render(im).save(os.path.join(OUT, fn), "JPEG", quality=82, optimize=True)
            cands.append(dict(series=name, file=fn, src=p["src"], pid=p["id"], score=p["score"],
                              w=p["w"], h=p["h"], url=p["url"], tags=p["tags"]))
            n += 1
        except Exception as e:
            print("   dl err", p.get("id"), type(e).__name__, flush=True)
        time.sleep(0.05)
    print("   previews=%d" % n, flush=True)

json.dump(cands, open("_tmp/candlow8.json", "w"), indent=1)
print("TOTAL candidates", len(cands), flush=True)
