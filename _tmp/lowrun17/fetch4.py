#!/usr/bin/env python3
"""Low-count run (17:00 IST, 2026-11-16) stage 1d: second source (danbooru) for thin series."""
import io, json, os, re, time
import requests
from PIL import Image, ImageFilter, ImageOps

UA = {"User-Agent": "AniPixBot/1.0 (wallpaper curation)",
      "Accept": "application/json"}

SERIES = [
    ("eminence in shadow",  ["kage_no_jitsuryokusha_ni_naritakute"]),
    ("akame ga kill",       ["akame_ga_kiru"]),
    ("kakegurui",           ["kakegurui"]),
    ("spice and wolf",      ["ookami_to_koushinryou"]),
    ("blue box",            ["ao_no_hako"]),
]

BAD = {"text", "english_text", "watermark", "signature", "artist_name", "speech_bubble", "comic", "4koma",
       "multiple_views", "character_sheet", "translated", "logo", "border", "framed", "letterboxed",
       "twitter_username", "web_address", "dated", "artist_logo", "english_commentary", "bad_id",
       "sketch", "monochrome", "greyscale", "partially_colored", "censored", "manga", "scan", "sample",
       "food", "chibi", "comic_panel", "bikini", "swimsuit", "underwear", "lingerie", "panties", "bra",
       "cleavage", "no_bra", "see_through", "spread_legs", "large_breasts", "huge_breasts", "ass",
       "nude", "naked", "topless", "wet", "bed", "bottomless", "sideboob", "underboob", "photo",
       "photograph", "cosplay", "screencap", "screenshot", "reference_sheet", "upscaled",
       "jpeg_artifacts", "lowres", "real_world_location", "photo_background", "collage", "crossover",
       "vector", "lineart", "line_art", "blood", "gore", "guro", "game_cg", "cgi",
       "anime_screencap", "screen_capture", "redraw", "official_art", "promotional_art",
       "key_visual", "poster", "banner", "album", "cover", "movie_poster", "bad_pixiv_id",
       "commentary", "commentary_request", "translation_request", "character_request", "artist_request",
       "wide_image", "phone_wallpaper", "variant_set", "resolution_mismatch", "partially_translated",
       "chinese_text", "korean_text", "japanese_text", "loli", "child",
       "aged_down", "muscular", "abs", "sweat", "tongue", "pov", "faceless_male", "male_focus",
       "greeting_card", "calendar", "sticker", "meme", "logo_parody", "parody", "fake_screenshot",
       "what", "why", "artist_request", "third-party_edit", "ai-generated", "ai_assisted"}

OUT = "_tmp/lowrun17"
PREV = os.path.join(OUT, "prev")
os.makedirs(PREV, exist_ok=True)
PER_SERIES = 24


def render(im, size=(360, 640)):
    w, h = im.size
    r = h / w
    tw, th = size
    t = 16 / 9
    if r > 2.2:
        bg = ImageOps.fit(im, (tw, th), method=Image.LANCZOS).filter(ImageFilter.GaussianBlur(22))
        fg = im.copy()
        fg.thumbnail((tw, th), Image.LANCZOS)
        bg.paste(fg, ((tw - fg.width) // 2, (th - fg.height) // 2))
        return bg
    if r > t:
        nh = int(w * t)
        y = int((h - nh) * 0.04)
        return im.crop((0, y, w, y + nh))
    nw = int(h / t)
    x = (w - nw) // 2
    return im.crop((x, 0, x + nw, h))


def get(url, params, timeout=60):
    for _ in range(3):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout)
            if r.status_code == 200:
                time.sleep(0.6)
                return r
            print("  HTTP", r.status_code, flush=True)
        except Exception as e:
            print("  ERR", type(e).__name__, flush=True)
        time.sleep(2)
    return None


def fetch(tag):
    out = []
    for page in (1, 2):
        r = get("https://danbooru.donmai.us/posts.json",
                {"tags": tag + " rating:general", "limit": 100, "page": page})
        if not r:
            break
        try:
            js = r.json()
        except Exception:
            break
        if not isinstance(js, list) or not js:
            break
        for p in js:
            out.append(dict(site="danbooru", id=p.get("id"), score=p.get("score") or 0,
                            w=p.get("image_width") or 0, h=p.get("image_height") or 0,
                            url=p.get("file_url") or p.get("large_file_url"),
                            prev=p.get("large_file_url") or p.get("preview_file_url") or p.get("file_url"),
                            tags=(p.get("tag_string_general") or "") + " " + (p.get("tag_string_copyright") or ""),
                            rating=p.get("rating")))
        if len(js) < 100:
            break
    return out


used = set()
uf = os.path.join(OUT, "used_pids.json")
if os.path.exists(uf):
    used = set("danbooru" + str(x) for x in json.load(open(uf)))
old = []
for cf in ("cands.json", "cands2.json", "cands3.json"):
    p2 = os.path.join(OUT, cf)
    if os.path.exists(p2):
        part = json.load(open(p2))
        old += part
        for c in part:
            used.add("%s%s" % (c.get("site"), c["pid"]))
start_idx = {}
for c in old:
    start_idx[c["series"]] = max(start_idx.get(c["series"], -1), c["idx"])

cands = []
for name, tags in SERIES:
    pool = []
    for t in tags:
        got = fetch(t)
        print("  %s tag %s -> %d" % (name, t, len(got)), flush=True)
        pool += got
    print("== %s: pool=%d" % (name, len(pool)), flush=True)

    seen, kept = set(), []
    pool.sort(key=lambda p: -(p["score"] or 0))
    for p in pool:
        key = "danbooru%s" % p["id"]
        if key in seen or key in used:
            continue
        seen.add(key)
        w, h = p["w"], p["h"]
        if not w or not h or not p.get("url") or not p.get("prev"):
            continue
        r = h / w
        if r >= 1.2:
            if h < 1300 or w < 700:
                continue
        elif r >= 0.85:
            if h < 1750:
                continue
        else:
            if h < 1700 or w < 2000:
                continue
        if set(p["tags"].split()) & BAD:
            continue
        kept.append(p)
    print("   valid=%d" % len(kept), flush=True)

    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    n = start_idx.get(name, -1) + 1
    added = 0
    for p in kept:
        if added >= PER_SERIES:
            break
        try:
            r = requests.get(p["prev"], headers=UA, timeout=90)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            fn = "%s_%02d.jpg" % (slug, n)
            render(im).save(os.path.join(PREV, fn), "JPEG", quality=84, optimize=True)
            cands.append(dict(series=name, slug=slug, idx=n, file=fn, pid=p["id"], site=p["site"],
                              score=p["score"], w=p["w"], h=p["h"], url=p["url"], tags=p["tags"][:400]))
            n += 1
            added += 1
        except Exception as e:
            print("   dl err", p.get("id"), type(e).__name__, flush=True)
        time.sleep(0.15)
    print("   previews=%d" % added, flush=True)

json.dump(cands, open(os.path.join(OUT, "cands4.json"), "w"), indent=1)
print("TOTAL new candidates", len(cands), flush=True)
