#!/usr/bin/env python3
"""Low-count run (17:00 IST, 2026-11-17) stage 1e: danbooru/konachan candidates for thin series."""
import io, json, os, re, time
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from collections import Counter

UA = {"User-Agent": "AniPixBot/1.0 (wallpaper curation)", "Accept": "application/json"}

SERIES = [
    ("code geass",        ["code_geass"]),
    ("cowboy bebop",      ["cowboy_bebop"]),
    ("toradora",          ["toradora"]),
    ("hyouka",            ["hyouka"]),
    ("your lie in april", ["shigatsu_wa_kimi_no_uso"]),
    ("steins gate",       ["steins;gate"]),
    ("made in abyss",     ["made_in_abyss"]),
    ("vinland saga",      ["vinland_saga"]),
    ("rurouni kenshin",   ["rurouni_kenshin"]),
    ("trigun",            ["trigun"]),
    ("hajime no ippo",    ["hajime_no_ippo"]),
    ("digimon",           ["digimon"]),
    ("fire force",        ["enen_no_shouboutai"]),
    ("gintama",           ["gintama"]),
]


BAD = {"text", "english_text", "watermark", "signature", "artist_name", "speech_bubble", "comic", "4koma",
       "multiple_views", "character_sheet", "translated", "logo", "border", "framed", "letterboxed",
       "twitter_username", "web_address", "dated", "artist_logo", "english_commentary", "bad_id",
       "sketch", "monochrome", "greyscale", "partially_colored", "censored", "manga", "scan", "sample",
       "chibi", "comic_panel", "bikini", "swimsuit", "underwear", "lingerie", "panties", "bra",
       "cleavage", "no_bra", "see_through", "spread_legs", "large_breasts", "huge_breasts", "ass",
       "nude", "naked", "topless", "wet", "bed", "bottomless", "sideboob", "underboob", "photo",
       "photograph", "cosplay", "screencap", "screenshot", "reference_sheet", "upscaled",
       "jpeg_artifacts", "lowres", "real_world_location", "photo_background", "collage", "crossover",
       "vector", "lineart", "line_art", "gore", "guro", "game_cg", "cgi",
       "anime_screencap", "screen_capture", "redraw", "promotional_art",
       "key_visual", "poster", "banner", "album", "cover", "movie_poster", "bad_pixiv_id",
       "translation_request", "character_request", "artist_request",
       "wide_image", "phone_wallpaper", "variant_set", "resolution_mismatch", "partially_translated",
       "chinese_text", "korean_text", "japanese_text", "loli", "child", "aged_down",
       "pov", "faceless_male", "greeting_card", "calendar", "sticker",
       "meme", "logo_parody", "fake_screenshot", "third-party_edit", "ai-generated",
       "ai_assisted", "censored_text", "bad_twitter_id", "bad_link", "translation_note"}

OUT = "_tmp/lowrun19"
PREV = os.path.join(OUT, "prev8")
SHEETS = os.path.join(OUT, "sheets8")
os.makedirs(PREV, exist_ok=True)
os.makedirs(SHEETS, exist_ok=True)
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


def get(url, params, timeout=50):
    for _ in range(3):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout)
            if r.status_code == 200:
                time.sleep(0.7)
                return r
            print("  HTTP", r.status_code, url, flush=True)
        except Exception as e:
            print("  ERR", type(e).__name__, flush=True)
        time.sleep(3)
    return None


def fetch_danbooru(tag):
    out = []
    for page in (1, 2, 3):
        r = get("https://konachan.net/post.json",
                {"tags": tag + " rating:s", "limit": 100, "page": page})
        if not r:
            break
        try:
            js = r.json()
        except Exception:
            break
        if not isinstance(js, list) or not js:
            break
        for p in js:
            out.append(dict(site="konachan", id=p.get("id"), score=p.get("score") or 0,
                            w=p.get("width") or 0, h=p.get("height") or 0,
                            url=p.get("file_url"),
                            prev=p.get("sample_url") or p.get("jpeg_url") or p.get("file_url"),
                            tags=p.get("tags") or "", rating=p.get("rating"), md5=p.get("md5")))
        if len(js) < 100:
            break
    return out


cands = []
seen_md5 = set()
for name, dtags in SERIES:
    pool = []
    for t in dtags:
        got = fetch_danbooru(t)
        print("  %s %s -> %d" % (name, t, len(got)), flush=True)
        pool += got
        if len(pool) >= 300:
            break
    print("== %s pool=%d" % (name, len(pool)), flush=True)

    seen, kept = set(), []
    pool.sort(key=lambda p: -(p["score"] or 0))
    for p in pool:
        pid = str(p["id"])
        if pid in seen:
            continue
        seen.add(pid)
        w, h = p["w"], p["h"]
        if not w or not h or not p.get("url") or not p.get("prev"):
            continue
        if p.get("md5") and p["md5"] in seen_md5:
            continue
        r = h / w
        if r >= 1.15:
            if h < 1000 or w < 600:
                continue
        elif r >= 0.85:
            if h < 1200:
                continue
        else:
            if w < 1600 or h < 900:
                continue
        if set(p["tags"].split()) & BAD:
            continue
        if p.get("rating") != "s":
            continue
        kept.append(p)
    print("   valid=%d" % len(kept), flush=True)

    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    n = 0
    for p in kept:
        if n >= PER_SERIES:
            break
        try:
            r = requests.get(p["prev"], headers=UA, timeout=60)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            fn = "%s_%02d.jpg" % (slug, n)
            render(im).save(os.path.join(PREV, fn), "JPEG", quality=84, optimize=True)
            cands.append(dict(series=name, slug=slug, idx=n, file=fn, pid=p["id"], site=p["site"],
                              score=p["score"], w=p["w"], h=p["h"], url=p["url"], tags=p["tags"][:400]))
            if p.get("md5"):
                seen_md5.add(p["md5"])
            n += 1
        except Exception as e:
            print("   dl err", p.get("id"), type(e).__name__, flush=True)
        time.sleep(0.15)
    print("   previews=%d" % n, flush=True)

json.dump(cands, open(os.path.join(OUT, "cands8.json"), "w"), indent=1)

COLS, ROWS = 5, 4
CW, CH = 300, 533
per = COLS * ROWS
byseries = {}
for c in cands:
    byseries.setdefault(c["slug"], []).append(c)
for slug, items in byseries.items():
    for si in range(0, len(items), per):
        chunk = items[si:si + per]
        sheet = Image.new("RGB", (COLS * CW, ROWS * CH), (18, 18, 18))
        dr = ImageDraw.Draw(sheet)
        for k, c in enumerate(chunk):
            im = Image.open(os.path.join(PREV, c["file"])).convert("RGB").resize((CW, CH), Image.LANCZOS)
            x, y = (k % COLS) * CW, (k // COLS) * CH
            sheet.paste(im, (x, y))
            dr.rectangle([x, y, x + 34, y + 20], fill=(0, 0, 0))
            dr.text((x + 5, y + 5), str(c["idx"]), fill=(255, 255, 0))
        sheet.save(os.path.join(SHEETS, "%s_%d.jpg" % (slug, si // per)), "JPEG", quality=86, optimize=True)

print("TOTAL candidates", len(cands), flush=True)
print("sheets:", sorted(os.listdir(SHEETS)), flush=True)
