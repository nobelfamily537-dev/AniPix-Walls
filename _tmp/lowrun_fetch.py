#!/usr/bin/env python3
"""Low-count run: fetch series-verified candidates from konachan.net (+safebooru fallback)."""
import os, io, json, time, re
import requests
from PIL import Image, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

# (display name, tag exactly as in AniPix tag index, alt name, category, booru tags to require)
SERIES = [
    ("soul eater", "soul eater", "soul eater", "anime", ["soul_eater"]),
    ("princess mononoke", "princess mononoke", "mononoke hime", "anime", ["mononoke_hime"]),
    ("dungeon meshi", "dungeon meshi", "delicious in dungeon", "anime", ["dungeon_meshi"]),
    ("zenless zone zero", "zenless zone zero", "zzz", "game", ["zenless_zone_zero"]),
    ("blue lock", "blue lock", "blue lock", "anime", ["blue_lock"]),
    ("spice and wolf", "ookami to koushinryou", "spice and wolf", "anime", ["ookami_to_koushinryou"]),
    ("sailor moon", "sailor moon", "bishoujo senshi sailor moon", "anime", ["sailor_moon"]),
    ("black clover", "black clover", "black clover", "anime", ["black_clover"]),
    ("one punch man", "one punch man", "one-punch man", "anime", ["one-punch_man"]),
    ("violet evergarden", "violet evergarden", "violet evergarden", "anime", ["violet_evergarden"]),
    # backups
    ("kaiju no. 8", "kaiju no. 8", "kaijuu 8-gou", "anime", ["kaijuu_8-gou"]),
    ("haikyuu", "haikyuu", "haikyuu!!", "anime", ["haikyuu!!"]),
    ("dan da dan", "dan da dan", "dandadan", "anime", ["dandadan"]),
    ("fullmetal alchemist", "fullmetal alchemist", "fma", "anime", ["fullmetal_alchemist"]),
    ("wind breaker", "wind breaker", "wind breaker", "anime", ["wind_breaker"]),
]
BACKUP = {"kaiju no. 8", "haikyuu", "dan da dan", "fullmetal alchemist", "wind breaker"}

BAD = {"text", "english_text", "watermark", "signature", "artist_name", "speech_bubble",
       "comic", "4koma", "multiple_views", "character_sheet", "translated", "logo", "border",
       "letterboxed", "twitter_username", "web_address", "dated", "artist_logo",
       "english_commentary", "bad_id", "sketch", "monochrome", "greyscale", "partially_colored",
       "gun", "mecha", "vehicle", "blood", "gore", "censored", "manga", "scan", "sample",
       "chibi", "comic_panel", "bikini", "swimsuit", "underwear", "lingerie", "panties", "bra",
       "cleavage", "no_bra", "see_through", "spread_legs", "large_breasts", "huge_breasts",
       "ass", "nude", "naked", "topless", "wet", "bed", "bottomless", "sideboob", "underboob",
       "photo", "photograph", "cosplay", "screencap", "screenshot", "reference_sheet",
       "concept_art", "lowres", "map", "real_world_location", "crossover", "3d", "cosplay_costume",
       "border", "framed", "quote", "lyrics"}

OUT = "_tmp/lowrun/prev"
os.makedirs(OUT, exist_ok=True)
PRIOR = set()
if os.path.exists("_tmp/prior_ids.txt"):
    PRIOR = {l.strip() for l in open("_tmp/prior_ids.txt") if l.strip()}


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
        y = int((h - nh) * (0.05 if r >= 1.6 else 0.18))
        return im.crop((0, y, w, y + nh))
    nw = int(h * t)
    x = (w - nw) // 2
    return im.crop((x, 0, x + nw, h))


def get(url, params=None, timeout=30):
    for _ in range(2):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout)
            if r.status_code == 200:
                time.sleep(1.0)
                return r
            print("  HTTP", r.status_code, url, flush=True)
        except Exception as e:
            print("  ERR", type(e).__name__, url, flush=True)
        time.sleep(2)
    return None


def konachan(btags):
    out = []
    for page in (1, 2, 3):
        r = get("https://konachan.net/post.json",
                {"tags": btags + " rating:s", "limit": 100, "page": page})
        if not r:
            break
        try:
            js = r.json()
        except Exception:
            break
        if not js:
            break
        for d in js:
            out.append(dict(src="konachan", pid="k%d" % d["id"], score=d.get("score") or 0,
                            w=d["width"], h=d["height"], url=d["jpeg_url"],
                            prev=d.get("sample_url") or d["jpeg_url"],
                            tags=(d.get("tags") or "").split()))
    return out


def safebooru(btags):
    out = []
    for page in (0, 1, 2):
        r = get("https://safebooru.org/index.php",
                {"page": "dapi", "s": "post", "q": "index", "json": 1,
                 "tags": btags + " sort:score:desc", "limit": 100, "pid": page})
        if not r:
            break
        try:
            js = r.json()
        except Exception:
            break
        if not js:
            break
        for d in js:
            d = {k.lower(): v for k, v in d.items()}
            try:
                w, h = int(d["width"]), int(d["height"])
            except Exception:
                continue
            out.append(dict(src="safebooru", pid="s%s" % d["id"], score=d.get("score") or 0,
                            w=w, h=h,
                            url="https://safebooru.org/images/%s/%s" % (d["directory"], d["image"]),
                            prev="https://safebooru.org/images/%s/%s" % (d["directory"], d["image"]),
                            tags=(d.get("tags") or "").split()))
    return out


cands = []
for name, tag, alt, cat, btags in SERIES:
    pool = []
    for bt in btags:
        pool += konachan(bt)
    print("== %s konachan=%d" % (name, len(pool)), flush=True)
    if len(pool) < 60:
        for bt in btags:
            pool += safebooru(bt)
        print("   +safebooru -> %d" % len(pool), flush=True)

    seen, kept = set(), []
    for p in pool:
        if p["pid"] in seen:
            continue
        seen.add(p["pid"])
        tg = set(p["tags"])
        if not (tg & set(btags)):
            continue
        if tg & BAD:
            continue
        r = p["h"] / p["w"]
        if not (1.25 <= r <= 2.4) and not (r <= 0.85 and p["w"] >= 1900):
            continue
        if p["h"] < 1200:
            continue
        kept.append(p)
    kept.sort(key=lambda p: (0 if p["h"] / p["w"] >= 1.25 else 1, -(p["score"] or 0)))
    print("   valid=%d" % len(kept), flush=True)

    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    lim = 10 if name in BACKUP else 20
    n = 0
    for p in kept:
        if n >= lim:
            break
        try:
            r = requests.get(p["prev"], headers=UA, timeout=60)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            if im.width < 400:
                continue
            fn = "%s_%02d.jpg" % (slug, n)
            render(im).save(os.path.join(OUT, fn), "JPEG", quality=82, optimize=True)
            cands.append(dict(series=name, tag=tag, alt=alt, cat=cat, file=fn, src=p["src"],
                              pid=p["pid"], score=p["score"], w=p["w"], h=p["h"],
                              url=p["url"], tags=p["tags"][:40]))
            n += 1
        except Exception as e:
            print("   dl err", p.get("pid"), type(e).__name__, flush=True)
        time.sleep(0.05)
    print("   previews=%d" % n, flush=True)

json.dump(cands, open("_tmp/lowrun/cand.json", "w"), indent=1)
print("TOTAL", len(cands), flush=True)
