#!/usr/bin/env python3
"""Low20 stage D: konachan candidates, previews rendered as the final 9:16 crop."""
import io, json, os, re, time
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json,text/plain,*/*",
      "Referer": "https://konachan.net/"}

SERIES = [
    ("ranma", "ranma", "ranma 1/2", "anime", ["saotome_ranma", "tendou_akane", "ranma_1/2"],
     ["saotome ranma", "tendou akane"]),
    ("digimon", "digimon", "digimon adventure", "anime",
     ["yagami_taichi", "angewomon", "digimon", "ishida_yamato"], ["yagami taichi", "angewomon"]),
    ("girls band cry", "girls band cry", None, "anime", ["girls_band_cry", "iseri_nina"], ["iseri nina"]),
    ("jigokuraku", "jigokuraku", "hell's paradise", "anime",
     ["yamada_asaemon_sagiri", "gabimaru", "jigokuraku"], ["yamada asaemon sagiri", "gabimaru"]),
    ("made in abyss", "made in abyss", None, "anime", ["nanachi", "ozen", "made_in_abyss"],
     ["nanachi", "ozen"]),
    ("yu-gi-oh", "yu-gi-oh", "yugioh", "anime", ["dark_magician_girl", "muto_yugi", "kaiba_seto"],
     ["dark magician girl", "muto yugi"]),
    ("dark souls", "dark souls", None, "game",
     ["artorias_the_abysswalker", "dark_suns_gwyndolin", "sister_friede", "dark_souls"],
     ["artorias", "gwyndolin"]),
    ("mushoku tensei", "mushoku tensei", "jobless reincarnation", "anime",
     ["eris_boreas_greyrat", "roxy_migurdia", "sylphiette", "mushoku_tensei"],
     ["eris boreas greyrat", "roxy migurdia", "sylphiette"]),
    ("persona 5", "persona 5", None, "game",
     ["takamaki_anne", "sakura_futaba", "niijima_makoto", "persona_5"],
     ["takamaki anne", "sakura futaba", "niijima makoto"]),
    ("steins gate", "steins gate", "steins;gate", "anime",
     ["makise_kurisu", "shiina_mayuri", "steins;gate"], ["makise kurisu"]),
    ("toradora", "toradora", None, "anime", ["aisaka_taiga", "kushieda_minori"], ["aisaka taiga"]),
    ("hyouka", "hyouka", None, "anime", ["chitanda_eru", "ibara_mayaka"], ["chitanda eru"]),
    ("serial experiments lain", "serial experiments lain", "lain", "anime",
     ["iwakura_lain", "serial_experiments_lain"], ["iwakura lain"]),
    ("nisekoi", "nisekoi", None, "anime", ["kirisaki_chitoge", "onodera_kosaki"], ["kirisaki chitoge"]),
    ("cowboy bebop", "cowboy bebop", None, "anime", ["faye_valentine", "spike_spiegel"], ["faye valentine"]),
    ("soul eater", "soul eater", None, "anime", ["maka_albarn", "soul_eater"], ["maka albarn"]),
    ("honkai impact", "honkai impact", "honkai impact 3rd", "game",
     ["kiana_kaslana", "raiden_mei", "bronya_zaychik"], ["kiana kaslana", "raiden mei"]),
    ("elden ring", "elden ring", None, "game", ["elden_ring", "ranni_the_witch"], ["ranni the witch"]),
]

BAD = {"text", "english_text", "watermark", "signature", "artist_name", "speech_bubble", "comic", "4koma",
       "multiple_views", "character_sheet", "translated", "logo", "border", "frame", "letterboxed",
       "twitter_username", "web_address", "dated", "artist_logo", "english_commentary", "bad_id",
       "sketch", "monochrome", "greyscale", "partially_colored", "censored", "manga", "scan", "sample",
       "chibi", "comic_panel", "bikini", "swimsuit", "underwear", "lingerie", "panties", "bra",
       "cleavage", "no_bra", "see_through", "spread_legs", "large_breasts", "huge_breasts", "ass",
       "nude", "naked", "topless", "wet", "bed", "bottomless", "sideboob", "underboob", "photo",
       "photograph", "cosplay", "screencap", "screenshot", "reference_sheet", "upscaled",
       "jpeg_artifacts", "lowres", "real_world_location", "photo_background", "collage", "crossover",
       "vector", "lineart", "line_art", "blood", "gore", "guro", "game_cg", "cgi",
       "anime_screencap", "screen_capture", "redraw", "official_art", "promotional_art",
       "key_visual", "poster", "banner", "album", "cover", "movie_poster", "bad_pixiv_id",
       "commentary", "commentary_request", "translation_request", "character_request", "artist_request",
       "wide_image", "phone_wallpaper", "variant_set", "resolution_mismatch", "partially_translated",
       "chinese_text", "korean_text", "japanese_text", "loli", "child", "aged_down", "muscular",
       "abs", "sweat", "tongue", "pov", "faceless_male", "male_focus", "greeting_card", "calendar",
       "sticker", "meme", "logo_parody", "fake_screenshot", "6+boys", "3boys", "smoking", "cigarette",
       "holding_gun", "gun", "food", "weapon_focus", "mecha_focus", "vehicle_focus", "text_focus",
       "sign", "banner_(object)"}

OUT = "_tmp/low20"
PREV = os.path.join(OUT, "prev3")
SHEETS = os.path.join(OUT, "sheets3")
os.makedirs(PREV, exist_ok=True)
os.makedirs(SHEETS, exist_ok=True)
PER_SERIES = 16


def crop916(im, focus=0.04):
    w, h = im.size
    t = 9 / 16
    r = h / w
    if r > 2.05:
        bg = ImageOps.fit(im, (1080, 1920), method=Image.LANCZOS).filter(ImageFilter.GaussianBlur(30))
        fg = im.copy()
        fg.thumbnail((1080, 1920), Image.LANCZOS)
        bg.paste(fg, ((1080 - fg.width) // 2, (1920 - fg.height) // 2))
        return bg
    if r > 1 / t:
        nh = int(w / t)
        y = int((h - nh) * focus)
        return im.crop((0, y, w, y + nh))
    nw = int(h * t)
    x = (w - nw) // 2
    return im.crop((x, 0, x + nw, h))


def get(base, tag):
    for _ in range(2):
        try:
            r = requests.get(base, params={"tags": tag + " rating:s", "limit": 100, "page": 1},
                             headers=UA, timeout=18)
            if r.status_code == 200:
                js = r.json()
                time.sleep(1.0)
                return [dict(site=base, id=p.get("id"), score=p.get("score") or 0,
                             w=p.get("width") or 0, h=p.get("height") or 0,
                             url=p.get("file_url"),
                             prev=p.get("sample_url") or p.get("jpeg_url") or p.get("file_url"),
                             tags=p.get("tags") or "", rating=p.get("rating")) for p in js]
            print("   HTTP", r.status_code, tag, flush=True)
        except Exception as e:
            print("   ERR", type(e).__name__, tag, flush=True)
        time.sleep(2)
    return []


cands = []
summary = {}
for name, itag, alt, cat, qtags, chars in SERIES:
    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    pool = []
    for t in qtags:
        got = get("https://konachan.net/post.json", t)
        print("  %-24s %-30s -> %d" % (name, t, len(got)), flush=True)
        pool += got
        if len(pool) >= 200:
            break
    seen, kept = set(), []
    pool.sort(key=lambda p: -(p["score"] or 0))
    for p in pool:
        if str(p["id"]) in seen:
            continue
        seen.add(str(p["id"]))
        w, h = p["w"], p["h"]
        if not w or not h or not p.get("url") or not p.get("prev"):
            continue
        r = h / w
        if r >= 1.15:
            if h < 1250 or w < 700:
                continue
        else:
            if w < 1900 or h < 1000:
                continue
        if set(p["tags"].split()) & BAD:
            continue
        if p.get("rating") not in ("s", None):
            continue
        kept.append(p)
    summary[name] = len(kept)
    print("== %-24s pool=%d valid=%d" % (name, len(pool), len(kept)), flush=True)

    n = 0
    for p in kept:
        if n >= PER_SERIES:
            break
        try:
            r = requests.get(p["prev"], headers=UA, timeout=45)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            fn = "%s_%02d.jpg" % (slug, n)
            crop916(im).resize((360, 640), Image.LANCZOS).save(os.path.join(PREV, fn), "JPEG",
                                                               quality=84, optimize=True)
            cands.append(dict(series=name, slug=slug, idx=n, file=fn, pid=p["id"], site=p["site"],
                              score=p["score"], w=p["w"], h=p["h"], url=p["url"], cat=cat,
                              itag=itag, alt=alt, chars=chars, tags=p["tags"]))
            n += 1
        except Exception as e:
            print("   dl err", p.get("id"), type(e).__name__, flush=True)
        time.sleep(0.15)
    print("   previews=%d" % n, flush=True)

json.dump(cands, open(os.path.join(OUT, "cands3.json"), "w"), indent=1)

COLS, ROWS = 4, 4
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
            try:
                im = Image.open(os.path.join(PREV, c["file"])).convert("RGB").resize((CW, CH), Image.LANCZOS)
            except Exception:
                im = Image.new("RGB", (CW, CH), (40, 40, 40))
            x, y = (k % COLS) * CW, (k // COLS) * CH
            sheet.paste(im, (x, y))
            dr.rectangle([x, y, x + 34, y + 20], fill=(0, 0, 0))
            dr.text((x + 5, y + 5), str(c["idx"]), fill=(255, 255, 0))
        sheet.save(os.path.join(SHEETS, "%s_%d.jpg" % (slug, si // per)), "JPEG", quality=86, optimize=True)

print("TOTAL", len(cands), flush=True)
print("SUMMARY", json.dumps(summary), flush=True)
