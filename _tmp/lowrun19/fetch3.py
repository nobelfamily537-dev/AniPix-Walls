#!/usr/bin/env python3
"""Low-count run (19:00 IST, 2026-11-19) stage 1b: broad per-series fetch (series + character tags)."""
import io, json, os, re, time
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json,text/plain,*/*",
      "Referer": "https://konachan.net/"}

SERIES_ALL = [
    ("a certain scientific railgun", ["to_aru_kagaku_no_railgun", "misaka_mikoto", "shirai_kuroko",
                                      "saten_ruiko", "uiharu_kazari"], set()),
    ("god eater", ["god_eater", "alisa_ilinichina_amiella", "soma_schicksal", "shio_(god_eater)",
                   "kamiya_ryou"], set()),
    ("erased", ["boku_dake_ga_inai_machi", "fujinuma_satoru", "hinazuki_kayo"], set()),
    ("the promised neverland", ["yakusoku_no_neverland", "emma_(yakusoku_no_neverland)",
                                "norman_(yakusoku_no_neverland)", "ray_(yakusoku_no_neverland)"], set()),
    ("the apothecary diaries", ["kusuriya_no_hitorigoto", "maomao_(kusuriya_no_hitorigoto)",
                                "jinshi_(kusuriya_no_hitorigoto)"], set()),
    ("fire force", ["enen_no_shouboutai", "tamaki_kotatsu", "arthur_boyle", "maki_ouze",
                    "iris_(enen_no_shouboutai)", "shinra_kusakabe"], set()),
    ("ponyo", ["gake_no_ue_no_ponyo", "ponyo_(character)", "sosuke_(gake_no_ue_no_ponyo)"], set()),
    ("porco rosso", ["kurenai_no_buta", "porco_rosso", "fio_piccolo"], set()),
    ("the wind rises", ["kaze_tachinu", "horikoshi_jirou", "satomi_naoko"], set()),
    ("hajime no ippo", ["hajime_no_ippo", "makunouchi_ippo", "takamura_mamoru"], set()),
    ("chiikawa", ["chiikawa", "chiikawa_(character)", "hachiware", "usagi_(chiikawa)"], set()),
    ("mashle", ["mashle", "mash_burnedead", "finn_ames", "lemon_irvine", "lance_crown", "dot_barrett"], set()),
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
       "greeting_card", "calendar", "sticker", "meme", "logo_parody", "parody", "fake_screenshot"}

OUT = "_tmp/lowrun19/d%d" % BATCH
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


def get(url, params, timeout=30):
    for _ in range(2):
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


def fetch_site(base, tag, pages=3):
    out = []
    for page in range(1, pages + 1):
        r = get(base, {"tags": tag + " rating:s", "limit": 100, "page": page})
        if not r:
            break
        try:
            js = r.json()
        except Exception:
            break
        if not isinstance(js, list) or not js:
            break
        for p in js:
            out.append(dict(site=base, id=p.get("id"), score=p.get("score") or 0,
                            w=p.get("width") or 0, h=p.get("height") or 0,
                            url=p.get("file_url"), prev=p.get("sample_url") or p.get("jpeg_url") or p.get("file_url"),
                            tags=p.get("tags") or "", rating=p.get("rating")))
        if len(js) < 100:
            break
    return out


used = set()
for d in ("_tmp/lowrun19", "_tmp/lowrun19/b0", "_tmp/lowrun19/b1", "_tmp/lowrun19/b2",
          "_tmp/lowrun19/c0", "_tmp/lowrun19/c1", "_tmp/lowrun19/c2"):
    uf = os.path.join(d, "used_pids.json")
    if os.path.exists(uf):
        try:
            used |= set(str(x) for x in json.load(open(uf)))
        except Exception:
            pass
for d in ("_tmp/lowrun19", "_tmp/lowrun19/b0", "_tmp/lowrun19/b1", "_tmp/lowrun19/b2",
          "_tmp/lowrun19/c0", "_tmp/lowrun19/c1", "_tmp/lowrun19/c2"):
    cf = os.path.join(d, "cands.json")
    if os.path.exists(cf):
        try:
            used |= set(str(c["pid"]) for c in json.load(open(cf)))
        except Exception:
            pass
print("already-used pids:", len(used), flush=True)

cands = []
for name, tags, ignore in SERIES:
    bad = BAD - ignore
    pool = []
    for t in tags:
        got = fetch_site("https://konachan.net/post.json", t)
        print("  %s tag %s -> %d" % (name, t, len(got)), flush=True)
        pool += got
        if len(pool) >= 260:
            break
    print("== %s: pool=%d" % (name, len(pool)), flush=True)

    seen, kept = set(), []
    rej = {"dup": 0, "dims": 0, "bad": 0, "rating": 0}
    pool.sort(key=lambda p: -(p["score"] or 0))
    for p in pool:
        if str(p["id"]) in seen or str(p["id"]) in used:
            rej["dup"] += 1
            continue
        seen.add(str(p["id"]))
        w, h = p["w"], p["h"]
        if not w or not h or not p.get("url") or not p.get("prev"):
            rej["dims"] += 1
            continue
        r = h / w
        if r >= 1.2:
            if h < 1300 or w < 700:
                rej["dims"] += 1
                continue
        elif r >= 0.85:
            if h < 1750:
                rej["dims"] += 1
                continue
        else:
            if h < 1700 or w < 2000:
                rej["dims"] += 1
                continue
        if set(p["tags"].split()) & bad:
            rej["bad"] += 1
            continue
        if p.get("rating") not in ("s", None):
            rej["rating"] += 1
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
                              score=p["score"], w=p["w"], h=p["h"], url=p["url"], tags=p["tags"][:400]))
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
