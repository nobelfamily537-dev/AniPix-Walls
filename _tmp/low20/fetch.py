#!/usr/bin/env python3
"""Low-count run (2026-11-18): stage 1 - fetch candidates (danbooru) + contact sheets."""
import io, json, os, re, time, hashlib
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": "AniPixBot/1.0 (wallpaper curation; contact nobelfamily537@gmail.com)"}
API = "https://danbooru.donmai.us/posts.json"

SERIES = [
    ("trigun",              ["trigun", "trigun_stampede"],                    "trigun stampede"),
    ("gintama",             ["gintama"],                                      "gintama'"),
    ("Hajime no Ippo",      ["hajime_no_ippo"],                               "fighting spirit"),
    ("the cat returns",     ["neko_no_onggaeshi"],                            "baron hatori"),
    ("spirited away",       ["sen_to_chihiro_no_kamikakushi"],                "sen to chihiro"),
    ("cardcaptor sakura",   ["cardcaptor_sakura"],                            "ccs"),
    ("cowboy bebop",        ["cowboy_bebop"],                                 "bebop"),
    ("code geass",          ["code_geass"],                                   "code geass lelouch of the rebellion"),
    ("horimiya",            ["horimiya"],                                     None),
    ("tales from earthsea", ["gedo_senki"],                                   "earthsea"),
    ("natsume yuujinchou",  ["natsume_yuujinchou"],                           "natsume's book of friends"),
    ("k-on",                ["k-on!"],                                        "k-on!"),
    ("vinland saga",        ["vinland_saga"],                                 None),
    ("mob psycho 100",      ["mob_psycho_100"],                               "mob psycho"),
    ("ponyo",               ["gake_no_ue_no_ponyo"],                          "ponyo on the cliff by the sea"),
    ("laputa",              ["tenkuu_no_shiro_laputa"],                       "castle in the sky"),
    ("sakamoto days",       ["sakamoto_days"],                                None),
    ("dandadan",            ["dandadan"],                                     None),
]

BAD = {"text", "english_text", "watermark", "signature", "artist_name", "speech_bubble", "comic", "4koma",
       "multiple_views", "character_sheet", "translated", "logo", "border", "frame", "letterboxed",
       "twitter_username", "web_address", "dated", "artist_logo", "english_commentary", "bad_id",
       "sketch", "monochrome", "greyscale", "partially_colored", "censored", "manga", "scan", "sample",
       "chibi", "comic_panel", "bikini", "swimsuit", "underwear", "lingerie", "cleavage", "no_bra",
       "see_through", "spread_legs", "large_breasts", "huge_breasts", "ass", "nude", "naked", "topless",
       "wet", "bed", "bottomless", "sideboob", "underboob", "photo", "photograph", "cosplay", "screencap",
       "screenshot", "reference_sheet", "upscaled", "jpeg_artifacts", "lowres", "real_world_location",
       "photo_background", "collage", "crossover", "vector", "lineart", "line_art", "blood", "gore",
       "game_cg", "cgi", "anime_screencap", "screen_capture", "redraw", "official_art", "promotional_art",
       "key_visual", "poster", "banner", "album", "cover", "movie_poster", "bad_pixiv_id",
       "commentary", "commentary_request", "translation_request", "character_request", "artist_request",
       "wide_image", "variant_set", "resolution_mismatch", "partially_translated", "chinese_text",
       "korean_text", "japanese_text", "loli", "child", "aged_down", "muscular", "abs", "sweat",
       "tongue", "pov", "faceless_male", "male_focus", "greeting_card", "calendar", "sticker", "meme",
       "logo_parody", "fake_screenshot", "real_photo", "photo_manipulation", "quote", "quotes",
       "censor_bar", "bar_censor", "mosaic_censoring", "artist_selfie", "bad_twitter_id", "bad_link",
       "md5_mismatch", "check_translation", "spoilers", "preview", "wallpaper_edit", "stereogram"}

OUT = "_tmp/low20"
PREV = os.path.join(OUT, "prev")
SHEETS = os.path.join(OUT, "sheets")
os.makedirs(PREV, exist_ok=True)
os.makedirs(SHEETS, exist_ok=True)
PER_SERIES = 20

data = json.load(open("wallpapers.json", encoding="utf-8"))
existing_ids = set()
for cat, items in data["categories"].items():
    for e in items:
        existing_ids.add(e["id"])


def wid_for(url):
    return "wpx" + hashlib.sha1(url.encode()).hexdigest()[:10]


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


def api(tag, page):
    for attempt in range(4):
        try:
            r = requests.get(API, params={"tags": tag, "limit": 200, "page": page}, headers=UA, timeout=45)
            if r.status_code == 200:
                time.sleep(1.0)
                return r.json()
            print("  HTTP", r.status_code, "tag", tag, "page", page, flush=True)
            if r.status_code == 429:
                time.sleep(6 + attempt * 4)
                continue
            if r.status_code == 422:
                return None
        except Exception as e:
            print("  ERR", type(e).__name__, flush=True)
        time.sleep(4)
    return None


def fetch(tag):
    out = []
    for page in (1, 2):
        js = api(tag + " rating:g score:>8 order:score", page)
        if not isinstance(js, list) or not js:
            break
        for p in js:
            u = p.get("file_url") or p.get("large_file_url")
            if not u:
                continue
            prev = p.get("large_file_url") or p.get("preview_file_url") or u
            out.append(dict(site="danbooru", id=p.get("id"), score=p.get("score") or 0,
                            w=p.get("image_width") or 0, h=p.get("image_height") or 0,
                            url=u, prev=prev, tags=p.get("tag_string") or "",
                            chars=p.get("tag_string_character") or "",
                            copyr=p.get("tag_string_copyright") or "",
                            rating=p.get("rating")))
        if len(js) < 200:
            break
    return out


cands = []
for name, tags, alt in SERIES:
    pool = []
    for t in tags:
        got = fetch(t)
        print("  %s tag %s -> %d" % (name, t, len(got)), flush=True)
        pool += got
        if len(pool) >= 300:
            break
    print("== %s: pool=%d" % (name, len(pool)), flush=True)

    seen, kept = set(), []
    pool.sort(key=lambda p: -(p["score"] or 0))
    for p in pool:
        if str(p["id"]) in seen:
            continue
        seen.add(str(p["id"]))
        w, h = p["w"], p["h"]
        if not w or not h or not p.get("url") or not p.get("prev"):
            continue
        if wid_for(p["url"]) in existing_ids:
            continue
        cw = min(w, h * 9.0 / 16.0)
        if cw < 800 or h < 1250:
            continue
        if set(p["tags"].split()) & BAD:
            continue
        if p.get("rating") not in ("g", None):
            continue
        kept.append(p)
    print("   valid=%d" % len(kept), flush=True)

    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    n = 0
    for p in kept:
        if n >= PER_SERIES:
            break
        try:
            r = requests.get(p["prev"], headers=UA, timeout=90)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            fn = "%s_%02d.jpg" % (slug, n)
            render(im).save(os.path.join(PREV, fn), "JPEG", quality=84, optimize=True)
            cands.append(dict(series=name, alt=alt, slug=slug, idx=n, file=fn, pid=str(p["id"]),
                              site=p["site"], score=p["score"], w=p["w"], h=p["h"], url=p["url"],
                              tags=p["tags"][:700], chars=p["chars"][:200], copyr=p["copyr"][:200]))
            n += 1
        except Exception as e:
            print("   dl err", p.get("id"), type(e).__name__, flush=True)
        time.sleep(0.2)
    print("   previews=%d" % n, flush=True)

json.dump(cands, open(os.path.join(OUT, "cands.json"), "w"), indent=1)

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
