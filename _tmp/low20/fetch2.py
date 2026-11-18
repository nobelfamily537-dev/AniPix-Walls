#!/usr/bin/env python3
"""Low-count run (2026-11-18): stage 1b - relaxed fill pass for thin series."""
import io, json, os, re, time, hashlib
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": "AniPixBot/1.0 (wallpaper curation; contact nobelfamily537@gmail.com)"}
API = "https://danbooru.donmai.us/posts.json"
OUT = "_tmp/low20"
PREV = os.path.join(OUT, "prev")
SHEETS = os.path.join(OUT, "sheets")
PER = 18

FILL = [
    ("spirited away",       "sen to chihiro",   ["ogino_chihiro", "haku_(sen_to_chihiro_no_kamikakushi)", "kaonashi", "yubaba"]),
    ("k-on",                "k-on!",            ["hirasawa_yui", "akiyama_mio", "tainaka_ritsu", "kotobuki_tsumugi", "nakano_azusa"]),
    ("code geass",          "code geass lelouch of the rebellion", ["lamperouge_lelouch", "c.c.", "kururugi_suzaku", "stadtfeld_kallen"]),
    ("trigun",              "trigun stampede",  ["vash_the_stampede", "nicholas_d._wolfwood", "meryl_stryfe", "millions_knives"]),
    ("mob psycho 100",      "mob psycho",       ["kageyama_shigeo", "reigen_arataka", "hanazawa_teruki", "kageyama_ritsu"]),
    ("laputa",              "castle in the sky",["sheeta_(laputa)", "pazu_(laputa)", "robot_(laputa)"]),
    ("horimiya",            None,               ["hori_kyouko", "miyamura_izumi", "yoshikawa_yuki", "ishikawa_toru"]),
    ("vinland saga",        None,               ["thorfinn_(vinland_saga)", "askeladd", "canute_(vinland_saga)"]),
    ("natsume yuujinchou",  "natsume's book of friends", ["natsume_takashi", "nyanko-sensei", "madara_(natsume_yuujinchou)"]),
    ("Hajime no Ippo",      "fighting spirit",  ["makunouchi_ippo", "takamura_mamoru", "miyata_ichirou"]),
    ("the cat returns",     "baron hatori",     ["baron_hatori", "haru_yoshioka", "muta_(neko_no_onggaeshi)"]),
    ("tales from earthsea", "earthsea",         ["therru", "arren_(gedo_senki)", "sparrowhawk"]),
    ("ponyo",               "ponyo on the cliff by the sea", ["ponyo_(gake_no_ue_no_ponyo)", "sosuke_(gake_no_ue_no_ponyo)"]),
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

data = json.load(open("wallpapers.json", encoding="utf-8"))
existing_ids = set()
for cat, items in data["categories"].items():
    for e in items:
        existing_ids.add(e["id"])

cands = json.load(open(os.path.join(OUT, "cands.json")))
have_pids = set(c["pid"] for c in cands)
have_urls = set(c["url"] for c in cands)


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
            print("  HTTP", r.status_code, tag, page, flush=True)
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
        js = api(tag + " rating:g score:>2 order:score", page)
        if not isinstance(js, list) or not js:
            break
        for p in js:
            u = p.get("file_url") or p.get("large_file_url")
            if not u:
                continue
            out.append(dict(site="danbooru", id=p.get("id"), score=p.get("score") or 0,
                            w=p.get("image_width") or 0, h=p.get("image_height") or 0,
                            url=u, prev=p.get("large_file_url") or p.get("preview_file_url") or u,
                            tags=p.get("tag_string") or "",
                            chars=p.get("tag_string_character") or "",
                            copyr=p.get("tag_string_copyright") or "",
                            rating=p.get("rating")))
        if len(js) < 200:
            break
    return out


added = {}
for name, alt, tags in FILL:
    pool = []
    for t in tags:
        got = fetch(t)
        print("  %s tag %s -> %d" % (name, t, len(got)), flush=True)
        pool += got
        if len(pool) >= 260:
            break
    print("== %s pool=%d" % (name, len(pool)), flush=True)

    seen, kept = set(), []
    pool.sort(key=lambda p: -(p["score"] or 0))
    for p in pool:
        pid = str(p["id"])
        if pid in seen or pid in have_pids:
            continue
        seen.add(pid)
        w, h = p["w"], p["h"]
        if not w or not h or not p.get("url") or not p.get("prev"):
            continue
        if wid_for(p["url"]) in existing_ids or p["url"] in have_urls:
            continue
        if min(w, h * 9.0 / 16.0) < 640 or h < 1000:
            continue
        if set(p["tags"].split()) & BAD:
            continue
        if p.get("rating") not in ("g", None):
            continue
        kept.append(p)
    print("   valid=%d" % len(kept), flush=True)

    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    start = 1 + max([c["idx"] for c in cands if c["slug"] == slug] or [-1])
    n = 0
    new = []
    for p in kept:
        if n >= PER:
            break
        try:
            r = requests.get(p["prev"], headers=UA, timeout=90)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            fn = "%s_%02d.jpg" % (slug, start + n)
            render(im).save(os.path.join(PREV, fn), "JPEG", quality=84, optimize=True)
            c = dict(series=name, alt=alt, slug=slug, idx=start + n, file=fn, pid=str(p["id"]),
                     site=p["site"], score=p["score"], w=p["w"], h=p["h"], url=p["url"],
                     tags=p["tags"][:700], chars=p["chars"][:200], copyr=p["copyr"][:200])
            new.append(c)
            have_pids.add(str(p["id"]))
            have_urls.add(p["url"])
            n += 1
        except Exception as e:
            print("   dl err", p.get("id"), type(e).__name__, flush=True)
        time.sleep(0.2)
    cands += new
    added[name] = len(new)
    print("   previews=%d" % n, flush=True)

    COLS, ROWS = 5, 4
    CW, CH = 300, 533
    for si in range(0, len(new), COLS * ROWS):
        chunk = new[si:si + COLS * ROWS]
        sheet = Image.new("RGB", (COLS * CW, ROWS * CH), (18, 18, 18))
        dr = ImageDraw.Draw(sheet)
        for k, c in enumerate(chunk):
            im = Image.open(os.path.join(PREV, c["file"])).convert("RGB").resize((CW, CH), Image.LANCZOS)
            x, y = (k % COLS) * CW, (k // COLS) * CH
            sheet.paste(im, (x, y))
            dr.rectangle([x, y, x + 34, y + 20], fill=(0, 0, 0))
            dr.text((x + 5, y + 5), str(c["idx"]), fill=(255, 255, 0))
        sheet.save(os.path.join(SHEETS, "fill-%s_%d.jpg" % (slug, si // (COLS * ROWS))), "JPEG", quality=86, optimize=True)

json.dump(cands, open(os.path.join(OUT, "cands.json"), "w"), indent=1)
print("ADDED", json.dumps(added), flush=True)
print("TOTAL candidates", len(cands), flush=True)
