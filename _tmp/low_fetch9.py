#!/usr/bin/env python3
"""Low-count run v9: safebooru (danbooru SFW) candidates - series-accurate fan art."""
import os, io, json, time, re
import requests
from PIL import Image, ImageFilter, ImageOps

UA = {"User-Agent": "AniPixBot/1.0 (wallpaper curation; contact nobelfamily537@gmail.com)"}
API = "https://safebooru.donmai.us/posts.json"

SERIES = [
    ("initial d", "initial_d"),
    ("pokemon", "pokemon"),
    ("detective conan", "detective_conan"),
    ("clannad", "clannad"),
    ("dragon ball super", "dragon_ball_super"),
    ("neon genesis evangelion", "neon_genesis_evangelion"),
    ("konosuba", "kono_subarashii_sekai_ni_shukufuku_wo!"),
    ("seven deadly sins", "nanatsu_no_taizai"),
    ("nausicaa", "kaze_no_tani_no_naushika"),
    ("berserk", "berserk"),
    ("howls moving castle", "howl_no_ugoku_shiro"),
    ("kaiju no 8", "kaijuu_8_gou"),
]

BAD = {"text", "english_text", "watermark", "signature", "artist_name", "speech_bubble", "comic", "4koma",
       "multiple_views", "character_sheet", "translated", "logo", "border", "frame", "letterboxed",
       "twitter_username", "web_address", "dated", "artist_logo", "english_commentary", "bad_id",
       "sketch", "monochrome", "greyscale", "partially_colored", "gun", "mecha", "vehicle", "blood",
       "gore", "censored", "manga", "scan", "sample", "food", "chibi", "comic_panel", "bikini",
       "swimsuit", "underwear", "lingerie", "panties", "bra", "cleavage", "no_bra", "see_through",
       "cameltoe", "spread_legs", "large_breasts", "huge_breasts", "ass", "nude", "naked", "topless",
       "wet", "bed", "bottomless", "sideboob", "underboob", "photo", "photograph", "cosplay",
       "screencap", "screenshot", "reference_sheet", "concept_art", "upscaled", "jpeg_artifacts",
       "lowres", "real_world_location", "photo_background", "abs", "midriff", "bikini_top",
       "solo_focus", "cover", "magazine", "poster", "collage", "parody", "crossover", "multiple_girls",
       "multiple_boys", "large_filesize"}

OUT = "_tmp/prevlow9"
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


def get(url, params, timeout=25):
    for _ in range(3):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout)
            if r.status_code == 200:
                time.sleep(1.1)
                return r
            print("  HTTP", r.status_code, flush=True)
        except Exception as e:
            print("  ERR", type(e).__name__, flush=True)
        time.sleep(3)
    return None


def search(tag):
    q = "%s rating:g -text -watermark -signature -comic -monochrome -greyscale -sketch -4koma -multiple_views -photo -cosplay" % tag
    r = get(API, {"tags": q, "limit": 100})
    if not r:
        return []
    try:
        return r.json()
    except Exception:
        return []


def ok(p):
    w, h = p.get("image_width") or 0, p.get("image_height") or 0
    if not w or not h or not p.get("file_url"):
        return False
    r = h / w
    if r >= 1.2:
        if h < 1300 or w < 700:
            return False
    elif r <= 0.8:
        if w < 1800:
            return False
    else:
        return False
    tg = set((p.get("tag_string") or "").split())
    if tg & BAD:
        return False
    return True


for name, tag in SERIES:
    pool = search(tag)
    print("== %s (%s): pool=%d" % (name, tag, len(pool)), flush=True)
    seen, kept = set(), []
    pool.sort(key=lambda p: -(p.get("fav_count") or 0))
    for p in pool:
        pid = p.get("id")
        if pid in seen:
            continue
        seen.add(pid)
        if ok(p):
            kept.append(p)
    print("   valid=%d" % len(kept), flush=True)

    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    n = 0
    for p in kept:
        if n >= 24:
            break
        url = p.get("large_file_url") or p.get("file_url")
        try:
            r = requests.get(url, headers=UA, timeout=30)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            fn = "%s_%02d.jpg" % (slug, n)
            render(im).save(os.path.join(OUT, fn), "JPEG", quality=82, optimize=True)
            cands.append(dict(series=name, tag=tag, file=fn, pid=p["id"],
                              score=p.get("fav_count") or 0, w=p["image_width"], h=p["image_height"],
                              url=p["file_url"], tags=(p.get("tag_string") or "")[:400]))
            n += 1
        except Exception as e:
            print("   dl err", p.get("id"), type(e).__name__, flush=True)
        time.sleep(0.4)
    print("   previews=%d" % n, flush=True)

json.dump(cands, open("_tmp/candlow9.json", "w"), indent=1)
print("TOTAL candidates", len(cands), flush=True)
