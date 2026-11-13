#!/usr/bin/env python3
"""Low-count run (2026-11-14): fetch wallhaven candidates for the emptiest series."""
import os, io, json, time, re
import requests
from PIL import Image, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

# (display name, tag exactly as in tag index, alt common name, category, queries)
SERIES = [
    ("soul eater", "soul eater", "soul eater", "anime",
     ["soul eater", "maka albarn", "soul evans", "death the kid", "soul eater evans", "black blood"]),
    ("princess mononoke", "princess mononoke", "mononoke hime", "anime",
     ["princess mononoke", "mononoke hime", "san mononoke", "studio ghibli", "ghibli forest", "kodama"]),
    ("dungeon meshi", "dungeon meshi", "delicious in dungeon", "anime",
     ["dungeon meshi", "marcille donato", "delicious in dungeon", "falin touden", "izutsumi", "laios touden"]),
    ("zenless zone zero", "zenless zone zero", "zzz", "game",
     ["zenless zone zero", "ellen joe", "miyabi", "zzz", "hoshimi miyabi", "qingyi"]),
    ("blue lock", "blue lock", "blue lock", "anime",
     ["blue lock", "isagi yoichi", "bachira meguru", "nagi seishiro", "chigiri hyoma", "michael kaiser"]),
    ("spice and wolf", "ookami to koushinryou", "spice and wolf", "anime",
     ["spice and wolf", "holo spice and wolf", "ookami to koushinryou", "holo wolf", "lawrence spice and wolf"]),
    ("sailor moon", "sailor moon", "bishoujo senshi sailor moon", "anime",
     ["sailor moon", "sailor moon crystal", "tsukino usagi", "sailor mars", "sailor venus", "super sailor moon"]),
    ("black clover", "black clover", "black clover", "anime",
     ["black clover", "asta black clover", "noelle silva", "yuno black clover", "nero black clover", "black bulls"]),
    ("one punch man", "one punch man", "one-punch man", "anime",
     ["one punch man", "saitama", "genos", "tatsumaki", "speed-o-sound sonic", "fubuki one punch man"]),
    ("violet evergarden", "violet evergarden", "violet evergarden", "anime",
     ["violet evergarden", "violet evergarden anime", "gilbert bougainvillea"]),
    # ---- backups, in case a primary series has no clean art ----
    ("kaiju no. 8", "kaiju no. 8", "kaijuu 8-gou", "anime",
     ["kaiju no 8", "kaiju no. 8", "kafka hibino", "kikoru shinomiya", "kaijuu 8-gou"]),
    ("haikyuu", "haikyuu", "haikyuu!!", "anime",
     ["haikyuu", "hinata shouyou", "kageyama tobio", "haikyuu!!"]),
    ("dan da dan", "dan da dan", "dandadan", "anime",
     ["dan da dan", "dandadan", "momo ayase", "okarun"]),
    ("berserk", "berserk", "berserk", "anime",
     ["berserk", "guts berserk", "griffith berserk", "kentaro miura"]),
    ("fullmetal alchemist", "fullmetal alchemist", "fma", "anime",
     ["fullmetal alchemist", "edward elric", "alphonse elric", "roy mustang"]),
    ("wind breaker", "wind breaker", "wind breaker", "anime",
     ["wind breaker", "sakura haruka", "bofurin", "suo hayato"]),
]

BACKUP_NAMES = {"kaiju no. 8", "haikyuu", "dan da dan", "berserk", "fullmetal alchemist", "wind breaker"}

BAD = {"text", "english_text", "watermark", "signature", "artist_name", "speech_bubble",
       "comic", "4koma", "multiple_views", "character_sheet", "translated", "logo", "border",
       "frame", "letterboxed", "twitter_username", "web_address", "dated", "artist_logo",
       "english_commentary", "bad_id", "sketch", "monochrome", "greyscale", "partially_colored",
       "gun", "mecha", "vehicle", "blood", "gore", "censored", "manga", "scan", "sample",
       "food", "chibi", "comic_panel", "bikini", "swimsuit", "underwear", "lingerie",
       "panties", "bra", "cleavage", "no_bra", "see_through", "spread_legs", "large_breasts",
       "huge_breasts", "ass", "nude", "naked", "topless", "wet", "bed", "bottomless",
       "sideboob", "underboob", "photo", "photograph", "cosplay", "screencap", "screenshot",
       "reference_sheet", "concept_art", "upscaled", "jpeg_artifacts", "lowres", "map",
       "real_world_location", "crossover", "3d", "cosplay_costume"}

OUT = "_tmp/lowrun/prev"
os.makedirs(OUT, exist_ok=True)
PRIOR = set()
if os.path.exists("_tmp/prior_ids.txt"):
    PRIOR = {l.strip() for l in open("_tmp/prior_ids.txt") if l.strip()}

PER_SERIES = 20


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


def get(url, params=None, timeout=20):
    for _ in range(2):
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
                {"q": q, "categories": "010", "purity": "100",
                 "atleast": "1080x1500",
                 "sorting": "favorites", "page": page})
        if not r:
            break
        try:
            js = r.json()
        except Exception:
            break
        for d in js.get("data", []):
            out.append(dict(id=d["id"], score=(d.get("favorites") or 0),
                            w=d["dimension_x"], h=d["dimension_y"], url=d["path"],
                            prev=(d.get("thumbs") or {}).get("large") or d["path"],
                            tags=[t["name"] for t in d.get("tags", [])],
                            colors=[c for c in (d.get("colors") or [])][:3]))
        if js.get("meta", {}).get("current_page", 1) >= js.get("meta", {}).get("last_page", 1):
            break
    return out


cands = []
for name, tag, alt, cat, queries in SERIES:
    pool = []
    for q in queries:
        pool += wallhaven(q)
    print("== %s pool=%d" % (name, len(pool)), flush=True)
    seen = set()
    pool.sort(key=lambda p: -(p["score"] or 0))
    kept = []
    for p in pool:
        if p["id"] in seen or p["id"] in PRIOR:
            continue
        seen.add(p["id"])
        tg = set(p["tags"])
        if tg & BAD:
            continue
        r = p["h"] / p["w"]
        if not (1.25 <= r <= 2.4) and not (r <= 0.8 and p["w"] >= 1900):
            continue
        kept.append(p)
    kept.sort(key=lambda p: (0 if p["h"] / p["w"] >= 1.25 else 1, -(p["score"] or 0)))
    print("   valid=%d" % len(kept), flush=True)

    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    lim = 10 if name in BACKUP_NAMES else PER_SERIES
    n = 0
    for p in kept:
        if n >= lim:
            break
        try:
            r = requests.get(p["prev"], headers=UA, timeout=25)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            print("   got", p["id"], im.size, len(r.content), flush=True)
            if im.width < 250:
                continue
            fn = "%s_%02d.jpg" % (slug, n)
            render(im).save(os.path.join(OUT, fn), "JPEG", quality=82, optimize=True)
            cands.append(dict(series=name, tag=tag, alt=alt, cat=cat, file=fn,
                              pid=p["id"], score=p["score"], w=p["w"], h=p["h"],
                              url=p["url"], tags=p["tags"], colors=p["colors"]))
            n += 1
        except Exception as e:
            print("   dl err", p.get("id"), type(e).__name__, flush=True)
        time.sleep(0.05)
    print("   previews=%d" % n, flush=True)

json.dump(cands, open("_tmp/lowrun/cand.json", "w"), indent=1)
print("TOTAL", len(cands), flush=True)
