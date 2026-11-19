#!/usr/bin/env python3
"""Low-count run (2026-11-20, 05:15 IST) stage 1: fetch candidates + contact sheets."""
import io, json, os, re, time
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json,text/plain,*/*",
      "Referer": "https://konachan.net/"}

# (display name, exact index tag, alt index tag or None, category, konachan tags, known characters)
SERIES = [
    ("ranma", "ranma", "ranma 1/2", "anime", ["ranma_1/2", "saotome_ranma", "tendou_akane"],
     ["saotome ranma", "tendou akane", "shampoo", "hibiki ryouga"]),
    ("god eater", "god eater", None, "game", ["god_eater"],
     ["alisa illinichina amiella", "soma schicksal", "kouta fujiki"]),
    ("ponyo", "ponyo", None, "anime", ["gake_no_ue_no_ponyo", "ponyo"],
     ["ponyo", "sousuke"]),
    ("porco rosso", "porco rosso", None, "anime", ["kurenai_no_buta", "porco_rosso"],
     ["porco rosso", "fio piccolo"]),
    ("bunny girl senpai", "bunny girl senpai", "rascal does not dream", "anime",
     ["seishun_buta_yarou"], ["sakurajima mai", "azusagawa sakuta", "koga tomoe"]),
    ("the wind rises", "the wind rises", "kaze tachinu", "anime", ["kaze_tachinu"],
     ["horikoshi jirou", "satomi naoko"]),
    ("vinland saga", "vinland saga", None, "anime", ["vinland_saga"],
     ["thorfinn", "askeladd", "canute"]),
    ("digimon", "digimon", "digimon adventure", "anime", ["digimon", "digimon_adventure"],
     ["agumon", "gabumon", "yagami taichi", "ishida yamato"]),
    ("girls band cry", "girls band cry", None, "anime", ["girls_band_cry"],
     ["iseri nina", "kawaragi momoka", "aikawa momoka"]),
    ("fire force", "fire force", "enen no shouboutai", "anime", ["enen_no_shouboutai"],
     ["shinra kusakabe", "tamaki kotatsu", "arthur boyle", "maki oze"]),
    ("noragami", "noragami", None, "anime", ["noragami"],
     ["yato", "iki hiyori", "yukine"]),
    ("rurouni kenshin", "rurouni kenshin", None, "anime", ["rurouni_kenshin"],
     ["himura kenshin", "kamiya kaoru"]),
    ("kuroko no basket", "kuroko no basket", "kuroko's basketball", "anime", ["kuroko_no_basket"],
     ["kuroko tetsuya", "kagami taiga", "aomine daiki", "kise ryouta"]),
    ("jigokuraku", "jigokuraku", "hell's paradise", "anime", ["jigokuraku"],
     ["gabimaru", "yamada asaemon sagiri"]),
    ("made in abyss", "made in abyss", None, "anime", ["made_in_abyss"],
     ["riko", "reg", "nanachi"]),
    ("yu-gi-oh", "yu-gi-oh", "yugioh", "anime", ["yu-gi-oh!"],
     ["muto yugi", "kaiba seto", "dark magician girl"]),
    ("akame ga kill", "akame ga kill", "akame ga kiru", "anime", ["akame_ga_kill"],
     ["akame", "tatsumi", "mine"]),
    ("mob psycho 100", "mob psycho 100", "mob psycho", "anime", ["mob_psycho_100"],
     ["kageyama shigeo", "reigen arataka", "dimple"]),
    ("gundam", "gundam", "mobile suit gundam", "anime", ["mobile_suit_gundam"],
     ["amuro ray", "char aznable"]),
    ("mushoku tensei", "mushoku tensei", "jobless reincarnation", "anime", ["mushoku_tensei"],
     ["rudeus greyrat", "eris boreas greyrat", "roxy migurdia", "sylphiette"]),
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
       "greeting_card", "calendar", "sticker", "meme", "logo_parody", "parody", "fake_screenshot",
       "multiple_boys", "2boys", "6+boys", "3boys", "smoking", "cigarette", "gun", "holding_gun"}

OUT = "_tmp/low20"
PREV = os.path.join(OUT, "prev")
SHEETS = os.path.join(OUT, "sheets")
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


def get(url, params, timeout=40):
    for _ in range(3):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout)
            if r.status_code == 200:
                time.sleep(0.8)
                return r
            print("  HTTP", r.status_code, url, flush=True)
        except Exception as e:
            print("  ERR", type(e).__name__, flush=True)
        time.sleep(4)
    return None


def fetch_site(base, tag):
    out = []
    for page in (1, 2, 3):
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
uf = os.path.join(OUT, "used_pids.json")
if os.path.exists(uf):
    used = set(str(x) for x in json.load(open(uf)))
print("already-used pids:", len(used), flush=True)

cands = []
for name, itag, alt, cat, tags, chars in SERIES:
    pool = []
    for t in tags:
        got = fetch_site("https://konachan.net/post.json", t)
        print("  %s tag %s -> %d" % (name, t, len(got)), flush=True)
        pool += got
        if len(pool) >= 220:
            break
    if len(pool) < 40:
        for t in tags:
            pool += fetch_site("https://yande.re/post.json", t)
    print("== %s: pool=%d" % (name, len(pool)), flush=True)

    seen, kept = set(), []
    pool.sort(key=lambda p: -(p["score"] or 0))
    for p in pool:
        if str(p["id"]) in seen or str(p["id"]) in used:
            continue
        seen.add(str(p["id"]))
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
        if p.get("rating") not in ("s", None):
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
                              score=p["score"], w=p["w"], h=p["h"], url=p["url"], cat=cat,
                              itag=itag, alt=alt, chars=chars, tags=p["tags"]))
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
