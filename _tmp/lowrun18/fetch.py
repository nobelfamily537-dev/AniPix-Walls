#!/usr/bin/env python3
"""Low-count run (2026-11-21) stage 1: fetch candidates + contact sheets."""
import io, json, os, re, time
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json,text/plain,*/*",
      "Referer": "https://konachan.net/"}

# (series tag key in index, display name, booru tag variants)
SERIES = [
    ("a silent voice",      "a silent voice",      ["koe_no_katachi", "nishimiya_shouko", "ishida_shouya"]),
    ("akatsuki no yona",    "akatsuki no yona",    ["akatsuki_no_yona", "yona_(akatsuki_no_yona)"]),
    ("food wars",           "food wars",           ["shokugeki_no_souma", "yukihira_souma", "tadokoro_megumi"]),
    ("the cat returns",     "the cat returns",     ["neko_no_onggaeshi", "baron_humbert_von_gikkingen", "haru_(neko_no_onggaeshi)"]),
    ("chihayafuru",         "chihayafuru",         ["chihayafuru", "ayase_chihaya"]),
    ("ponyo",               "ponyo",               ["gake_no_ue_no_ponyo", "ponyo_(gake_no_ue_no_ponyo)"]),
    ("porco rosso",         "porco rosso",         ["kurenai_no_buta", "porco_rosso"]),
    ("kill la kill",        "kill la kill",        ["kill_la_kill", "matoi_ryuuko", "kiryuin_satsuki"]),
    ("the wind rises",      "the wind rises",      ["kaze_tachinu", "horikoshi_jirou", "satomi_naoko"]),
    ("oregairu",            "oregairu",            ["yahari_ore_no_seishun_love_comedy_wa_machigatteiru", "yukinoshita_yukino", "yuigahama_yui"]),
    ("bubble",              "bubble",              ["bubble_(film)", "utai_(bubble)"]),
    ("vinland saga",        "vinland saga",        ["vinland_saga", "thorfinn_(vinland_saga)", "askeladd"]),
    ("seven deadly sins",   "seven deadly sins",   ["nanatsu_no_taizai", "elizabeth_liones", "meliodas"]),
    ("rurouni kenshin",     "rurouni kenshin",     ["rurouni_kenshin", "himura_kenshin", "kamiya_kaoru"]),
    ("noragami",            "noragami",            ["noragami", "yato_(noragami)", "ikishima_hiori"]),
    ("fire force",          "fire force",          ["enen_no_shouboutai", "tamaki_kotatsu"]),
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
       "anime_screencap", "screen_capture", "redraw", "official_art", "promotional_art",
       "key_visual", "poster", "banner", "album", "cover", "movie_poster", "bad_pixiv_id",
       "commentary", "commentary_request", "translation_request", "character_request", "artist_request",
       "wide_image", "phone_wallpaper", "variant_set", "resolution_mismatch", "partially_translated",
       "chinese_text", "korean_text", "japanese_text", "loli", "child",
       "aged_down", "muscular", "abs", "sweat", "tongue", "pov", "faceless_male", "male_focus",
       "greeting_card", "calendar", "sticker", "meme", "logo_parody", "fake_screenshot",
       "crying", "tears", "snot", "injury", "wound", "smoking", "cigarette", "alcohol", "drunk",
       "gun", "weapon", "blood_on_face", "scared", "angry", "screaming", "torn_clothes"}

OUT = "_tmp/lowrun18"
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


def get(url, params, timeout=40):
    for _ in range(3):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout)
            if r.status_code == 200:
                time.sleep(0.7)
                return r
            print("  HTTP", r.status_code, url, flush=True)
        except Exception as e:
            print("  ERR", type(e).__name__, flush=True)
        time.sleep(4)
    return None


def fetch_site(base, tag, pages=(1, 2, 3)):
    out = []
    for page in pages:
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
                            url=p.get("file_url"),
                            prev=p.get("sample_url") or p.get("jpeg_url") or p.get("file_url"),
                            tags=p.get("tags") or "", rating=p.get("rating")))
        if len(js) < 100:
            break
    return out


# ---- dedupe against everything already in the app -------------------------
import hashlib
data = json.load(open("wallpapers.json", encoding="utf-8"))
existing_ids, existing_urls = set(), set()
for cat, items in data["categories"].items():
    for e in items:
        existing_ids.add(e["id"])
        for k in ("full", "thumb", "alt"):
            if e.get(k):
                existing_urls.add(e[k])
print("existing ids:", len(existing_ids), flush=True)


def wid_for(url):
    return "wpx" + hashlib.sha1(url.encode()).hexdigest()[:10]


used = set()
for fn in ("used_pids.json", "used_pids2.json"):
    p = os.path.join(OUT, fn)
    if os.path.exists(p):
        used |= set(str(x) for x in json.load(open(p)))
print("already-used pids:", len(used), flush=True)

cands = []
for key, name, tags in SERIES:
    bad = set(BAD)
    pool = []
    for t in tags:
        got = fetch_site("https://konachan.net/post.json", t)
        print("  %s tag %s -> %d" % (key, t, len(got)), flush=True)
        pool += got
        if len(pool) >= 220:
            break
    if len(pool) < 40:
        for t in tags:
            got = fetch_site("https://yande.re/post.json", t)
            print("  %s YANDE tag %s -> %d" % (key, t, len(got)), flush=True)
            pool += got
    print("== %s: pool=%d" % (key, len(pool)), flush=True)

    seen, kept = set(), []
    pool.sort(key=lambda p: -(p["score"] or 0))
    for p in pool:
        u = p.get("url")
        if not u or str(p["id"]) in seen or str(p["id"]) in used:
            continue
        seen.add(str(p["id"]))
        if u in existing_urls or wid_for(u) in existing_ids:
            continue
        w, h = p["w"], p["h"]
        if not w or not h or not p.get("prev"):
            continue
        r = h / w
        if r >= 1.2:
            if h < 1200 or w < 640:
                continue
        elif r >= 0.85:
            if h < 1700:
                continue
        else:
            if h < 1600 or w < 1900:
                continue
        if set(p["tags"].split()) & bad:
            continue
        if p.get("rating") not in ("s", None):
            continue
        kept.append(p)
    print("   valid=%d" % len(kept), flush=True)

    slug = re.sub(r"[^a-z0-9]+", "-", key).strip("-")
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
            cands.append(dict(series=key, name=name, slug=slug, idx=n, file=fn, pid=p["id"], site=p["site"],
                              score=p["score"], w=p["w"], h=p["h"], url=p["url"], tags=p["tags"]))
            used.add(str(p["id"]))
            n += 1
        except Exception as e:
            print("   dl err", p.get("id"), type(e).__name__, flush=True)
        time.sleep(0.2)
    print("   previews=%d" % n, flush=True)

json.dump(cands, open(os.path.join(OUT, "cands.json"), "w"), indent=1)
json.dump(sorted(used), open(os.path.join(OUT, "used_pids.json"), "w"))

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
