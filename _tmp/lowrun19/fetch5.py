#!/usr/bin/env python3
"""Low-count run (19:00 IST, 2026-11-19) stage 1c: danbooru fetch + contact sheets."""
import io, json, os, re, time
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": "AniPixBot/1.0 (wallpaper curation)"}
API = "https://danbooru.donmai.us"

SERIES_ALL = [
    ("the promised neverland",        ["yakusoku_no_neverland"], set()),
    ("god eater",                     ["god_eater"], set()),
    ("hajime no ippo",                ["hajime_no_ippo"], set()),
    ("chiikawa",                      ["chiikawa"], set()),
    ("the wind rises",                ["kaze_tachinu"], set()),
    ("porco rosso",                   ["kurenai_no_buta"], set()),
    ("tales from earthsea",           ["gedo_senki"], set()),
    ("ponyo",                         ["gake_no_ue_no_ponyo"], set()),
    ("vinland saga",                  ["vinland_saga"], set()),
    ("mashle",                        ["mashle"], set()),
    ("erased",                        ["boku_dake_ga_inai_machi"], set()),
    ("the apothecary diaries",        ["kusuriya_no_hitorigoto"], set()),
    ("a certain scientific railgun",  ["to_aru_kagaku_no_railgun"], set()),
    ("horimiya",                      ["hori-san_to_miyamura-kun", "horimiya"], set()),
    ("86",                            ["86_(eighty_six)", "eighty_six", "86_-_eighty_six-", "86_(novel)", "eighty-six_(anime)"], set()),
    ("fire force",                    ["enen_no_shouboutai", "fire_force"], set()),
    ("the cat returns",               ["the_cat_returns", "neko_no_onggaeshi"], set()),
    ("from up on poppy hill",         ["kokuriko_zaka_kara", "from_up_on_poppy_hill", "kokuriko-zaka_kara"], set()),
]

BATCH = int(os.environ.get("BATCH", "0"))
SERIES = SERIES_ALL[BATCH::3]

BAD = {"text", "english_text", "watermark", "signature", "artist_name", "speech_bubble", "comic", "4koma",
       "multiple_views", "character_sheet", "translated", "logo", "border", "frame", "letterboxed",
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
       "animated", "ugoira", "video", "gif", "webm", "pixel_art", "screencap", "sample_watermark",
       "english_text", "artist_logo", "character_name", "dialogue", "speech", "manga_cover",
       "doujinshi_cover", "magazine_cover", "book", "sketchbook", "line_art", "colored_sketch",
       "multiple_boys", "no_humans", "scenery", "landscape"}

OUT = "_tmp/lowrun19/f%d" % BATCH
PREV = os.path.join(OUT, "prev")
SHEETS = os.path.join(OUT, "sheets")
os.makedirs(PREV, exist_ok=True)
os.makedirs(SHEETS, exist_ok=True)

PER_SERIES = 20


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


def api(path, params, timeout=40):
    for _ in range(3):
        try:
            r = requests.get(API + path, params=params, headers=UA, timeout=timeout)
            if r.status_code == 200:
                time.sleep(0.5)
                return r.json()
            print("  HTTP", r.status_code, path, flush=True)
            if r.status_code in (429, 503):
                time.sleep(6)
                continue
            return None
        except Exception as e:
            print("  ERR", type(e).__name__, flush=True)
        time.sleep(3)
    return None


cands = []
for name, tags, ignore in SERIES:
    bad = BAD - ignore
    pool, seen = [], set()
    for t in tags:
        got = 0
        for page in (1, 2, 3):
            js = api("/posts.json", {"tags": t + " rating:g", "limit": 200, "page": page,
                                     "only": "id,image_width,image_height,file_url,large_file_url,"
                                             "preview_file_url,score,fav_count,file_ext,"
                                             "tag_string_character,tag_string_copyright,tag_string_general"})
            if not js:
                break
            for p in js:
                if p.get("id") in seen:
                    continue
                seen.add(p.get("id"))
                pool.append(dict(site="danbooru", id=p.get("id"), score=p.get("score") or 0,
                                 fav=p.get("fav_count") or 0, w=p.get("image_width") or 0,
                                 h=p.get("image_height") or 0, url=p.get("file_url"),
                                 prev=p.get("large_file_url") or p.get("preview_file_url") or p.get("file_url"),
                                 ext=p.get("file_ext"),
                                 chars=p.get("tag_string_character") or "",
                                 copy=p.get("tag_string_copyright") or "",
                                 gen=p.get("tag_string_general") or ""))
                got += 1
            if len(js) < 200:
                break
        print("  %s tag %s -> %d" % (name, t, got), flush=True)
        if len(pool) >= 260:
            break
    print("== %s: pool=%d" % (name, len(pool)), flush=True)

    kept, rej = [], {"dims": 0, "bad": 0, "ext": 0}
    pool.sort(key=lambda p: -(p["fav"] * 3 + p["score"]))
    for p in pool:
        w, h = p["w"], p["h"]
        if not w or not h or not p.get("url"):
            rej["dims"] += 1
            continue
        if p.get("ext") not in ("jpg", "jpeg", "png"):
            rej["ext"] += 1
            continue
        crop_h = min(h, w * 16.0 / 9.0)
        if crop_h < 1400 or w < 750:
            rej["dims"] += 1
            continue
        if set(p["gen"].split()) & bad:
            rej["bad"] += 1
            continue
        kept.append(p)
    print("   valid=%d rej=%s" % (len(kept), rej), flush=True)

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
                              score=p["score"], fav=p["fav"], w=p["w"], h=p["h"], url=p["url"],
                              chars=p["chars"][:120], copy=p["copy"][:80], gen=p["gen"][:400]))
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
