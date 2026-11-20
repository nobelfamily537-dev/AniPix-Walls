#!/usr/bin/env python3
"""Low-count run stage 1b: yande.re candidates + contact sheets, parallel downloads."""
import io, json, os, re, time
from concurrent.futures import ThreadPoolExecutor
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Referer": "https://yande.re/"}

SERIES = [
    ("chiikawa",             ["chiikawa", "chiikawa_(anime)", "hachiware_(chiikawa)"], set()),
    ("uzumaki",              ["uzumaki_(junji_ito)", "uzumaki"], {"uzumaki"}),
    ("natsume yuujinchou",   ["natsume_yuujinchou", "natsume_takashi"], set()),
    ("initial d",            ["initial_d", "fujiwara_takumi"], set()),
    ("tales from earthsea",  ["tales_from_earthsea", "ged_senki_tan"], set()),
    ("chihayafuru",          ["chihayafuru", "ayase_chihaya"], set()),
    ("the cat returns",      ["neko_no_ongeshi", "neko_no_ongaeshi", "baron_humbert_von_gikkingen"], set()),
    ("my dress up darling",  ["sono_bisque_doll_wa_koi_wo_suru", "kitagawa_marin"], set()),
    ("ranma 1/2",            ["ranma_1/2", "saotome_ranma", "tendou_akane"], set()),
    ("gurren lagann",        ["tengen_toppa_gurren_lagann", "yoko_littner"], set()),
    ("ponyo",                ["gake_no_ue_no_ponyo", "ponyo_(character)"], set()),
    ("bunny girl senpai",    ["rascal_does_not_dream_of_bunny_girl_senpai", "sakurajima_mai"], set()),
    ("oregairu",             ["yahari_ore_no_seishun_love_comedy_wa_machigatteiru", "yukinoshita_yukino"], set()),
    ("the wind rises",       ["kaze_tachinu", "naoko_(kaze_tachinu)"], set()),
    ("vinland saga",         ["vinland_saga", "thorfinn_(vinland_saga)"], set()),
]

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
       "anime_screencap", "screen_capture", "redraw", "promotional_art",
       "key_visual", "poster", "banner", "album", "cover", "movie_poster", "bad_pixiv_id",
       "commentary", "commentary_request", "translation_request", "character_request", "artist_request",
       "wide_image", "variant_set", "resolution_mismatch", "partially_translated",
       "chinese_text", "korean_text", "japanese_text", "loli", "child",
       "aged_down", "muscular", "abs", "sweat", "tongue", "pov", "faceless_male", "male_focus",
       "greeting_card", "calendar", "sticker", "meme", "logo_parody", "fake_screenshot", "back",
       "seiyuu", "voice_actor", "magazine", "book", "dakimakura", "pillow", "figure", "toy", "3d",
       "real_life", "photo_(medium)", "cartoon", "western", "comic_book", "greyscale_image"}

OUT = "_tmp/low18b"
PREV = os.path.join(OUT, "prev")
SHEETS = os.path.join(OUT, "sheets")
os.makedirs(PREV, exist_ok=True)
os.makedirs(SHEETS, exist_ok=True)
PER_SERIES = 16


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


def fetch_site(tag):
    out = []
    for page in (1, 2, 3):
        for attempt in range(2):
            try:
                r = requests.get("https://yande.re/post.json",
                                 params={"tags": tag + " rating:s", "limit": 100, "page": page},
                                 headers=UA, timeout=25)
                if r.status_code != 200:
                    print("  HTTP", r.status_code, tag, flush=True)
                    time.sleep(3)
                    continue
                js = r.json()
                break
            except Exception as e:
                print("  ERR", type(e).__name__, tag, flush=True)
                time.sleep(3)
        else:
            break
        if not isinstance(js, list) or not js:
            break
        for p in js:
            out.append(dict(site="yande", id=p.get("id"), score=p.get("score") or 0,
                            w=p.get("width") or 0, h=p.get("height") or 0,
                            url=p.get("file_url"),
                            prev=p.get("sample_url") or p.get("jpeg_url") or p.get("file_url"),
                            tags=p.get("tags") or "", rating=p.get("rating")))
        if len(js) < 100:
            break
    print("  tag %s -> %d" % (tag, len(out)), flush=True)
    return out


def dl(job):
    p, path = job
    for _ in range(2):
        try:
            r = requests.get(p["prev"], headers=UA, timeout=25)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            render(im).save(path, "JPEG", quality=84, optimize=True)
            return True
        except Exception as e:
            err = type(e).__name__
            time.sleep(2)
    print("   dl err", p.get("id"), err, flush=True)
    return False


used = set()
for f in ("_tmp/low18/used_pids.json", "_tmp/low18b/used_pids.json"):
    if os.path.exists(f):
        try:
            used |= set(str(x) for x in json.load(open(f)))
        except Exception:
            pass

cands = []
for name, tags, ignore in SERIES:
    bad = BAD - ignore
    pool = []
    for t in tags:
        pool += fetch_site(t)
        if len(pool) >= 150:
            break
    print("== %s: pool=%d" % (name, len(pool)), flush=True)
    seen, kept = set(), []
    pool.sort(key=lambda p: -(p["score"] or 0))
    for p in pool:
        key = "%s:%s" % (p["site"], p["id"])
        if key in seen or str(p["id"]) in used:
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
        if set(p["tags"].split()) & bad:
            continue
        if p.get("rating") not in ("s", None):
            continue
        kept.append(p)
    print("   valid=%d" % len(kept), flush=True)
    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    take = kept[:PER_SERIES]
    jobs = [(p, os.path.join(PREV, "%s_%02d.jpg" % (slug, i))) for i, p in enumerate(take)]
    with ThreadPoolExecutor(max_workers=8) as ex:
        oks = list(ex.map(dl, jobs))
    n = 0
    for (p, path), ok in zip(jobs, oks):
        if not ok:
            continue
        cands.append(dict(series=name, slug=slug, idx=n, file=os.path.basename(path), pid=p["id"],
                          site=p["site"], score=p["score"], w=p["w"], h=p["h"], url=p["url"],
                          tags=p["tags"][:400]))
        n += 1
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
