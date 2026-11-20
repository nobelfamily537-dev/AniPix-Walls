#!/usr/bin/env python3
"""Low20 stage C: wallpaper-grade candidates from konachan/yande.re by character tags."""
import io, json, os, re, time
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json,text/plain,*/*",
      "Referer": "https://konachan.net/"}

# (name, exact index tag, alt index tag, category, query tags, known characters)
SERIES = [
    ("ranma", "ranma", "ranma 1/2", "anime", ["saotome_ranma", "tendou_akane", "ranma_1/2"],
     ["saotome ranma", "tendou akane"]),
    ("digimon", "digimon", "digimon adventure", "anime",
     ["yagami_taichi", "ishida_yamato", "angewomon", "digimon"], ["yagami taichi", "angewomon"]),
    ("girls band cry", "girls band cry", None, "anime", ["girls_band_cry", "iseri_nina"], ["iseri nina"]),
    ("jigokuraku", "jigokuraku", "hell's paradise", "anime",
     ["yamada_asaemon_sagiri", "gabimaru", "jigokuraku"], ["yamada asaemon sagiri", "gabimaru"]),
    ("made in abyss", "made in abyss", None, "anime", ["nanachi", "ozen", "faputa", "made_in_abyss"],
     ["nanachi", "ozen"]),
    ("yu-gi-oh", "yu-gi-oh", "yugioh", "anime", ["dark_magician_girl", "muto_yugi", "kaiba_seto"],
     ["dark magician girl", "muto yugi"]),
    ("dark souls", "dark souls", None, "game",
     ["artorias_the_abysswalker", "dark_suns_gwyndolin", "sister_friede", "crossbreed_priscilla",
      "dark_souls"], ["artorias", "gwyndolin"]),
    ("mushoku tensei", "mushoku tensei", "jobless reincarnation", "anime",
     ["eris_boreas_greyrat", "roxy_migurdia", "sylphiette", "mushoku_tensei"],
     ["eris boreas greyrat", "roxy migurdia", "sylphiette"]),
    ("persona 5", "persona 5", None, "game",
     ["takamaki_anne", "sakura_futaba", "niijima_makoto", "yoshizawa_kasumi", "persona_5"],
     ["takamaki anne", "sakura futaba", "niijima makoto"]),
    ("heavenly delusion", "heavenly delusion", "tengoku daimakyou", "anime",
     ["kiruko_(tengoku_daimakyou)", "tengoku_daimakyou"], ["kiruko"]),
    ("steins gate", "steins gate", "steins;gate", "anime",
     ["makise_kurisu", "shiina_mayuri", "steins;gate"], ["makise kurisu"]),
    ("toradora", "toradora", None, "anime", ["aisaka_taiga", "kushieda_minori", "kawashima_ami"],
     ["aisaka taiga", "kushieda minori"]),
    ("hyouka", "hyouka", None, "anime", ["chitanda_eru", "ibara_mayaka"], ["chitanda eru"]),
    ("serial experiments lain", "serial experiments lain", "lain", "anime",
     ["iwakura_lain", "serial_experiments_lain"], ["iwakura lain"]),
    ("nisekoi", "nisekoi", None, "anime", ["kirisaki_chitoge", "onodera_kosaki"], ["kirisaki chitoge"]),
    ("cowboy bebop", "cowboy bebop", None, "anime", ["faye_valentine", "spike_spiegel"], ["faye valentine"]),
    ("elden ring", "elden ring", None, "game",
     ["ranni_the_witch", "malenia_blade_of_miquella", "melina_(elden_ring)"], ["ranni the witch", "malenia"]),
    ("soul eater", "soul eater", None, "anime", ["maka_albarn", "crona_(soul_eater)"], ["maka albarn"]),
    ("honkai impact", "honkai impact", "honkai impact 3rd", "game",
     ["kiana_kaslana", "raiden_mei", "bronya_zaychik"], ["kiana kaslana", "raiden mei"]),
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
       "english_text", "sign", "banner_(object)"}

OUT = "_tmp/low20"
PREV = os.path.join(OUT, "prev2")
SHEETS = os.path.join(OUT, "sheets2")
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


def get(base, tag, pages=(1, 2)):
    out = []
    for page in pages:
        js = None
        for _ in range(2):
            try:
                r = requests.get(base, params={"tags": tag + " rating:s", "limit": 100, "page": page},
                                 headers=UA, timeout=20)
                if r.status_code == 200:
                    js = r.json()
                    time.sleep(1.2)
                    break
                print("   HTTP", r.status_code, tag, page, flush=True)
            except Exception as e:
                print("   ERR", type(e).__name__, tag, page, flush=True)
            time.sleep(2)
        if not js:
            break
        for p in js:
            out.append(dict(site=base, id=p.get("id"), score=p.get("score") or 0,
                            w=p.get("width") or 0, h=p.get("height") or 0,
                            url=p.get("file_url"), prev=p.get("sample_url") or p.get("jpeg_url") or p.get("file_url"),
                            tags=p.get("tags") or "", rating=p.get("rating")))
        if len(js) < 100:
            break
    return out


cands = []
summary = {}
for name, itag, alt, cat, qtags, chars in SERIES:
    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    pool = []
    for t in qtags:
        got = get("https://konachan.net/post.json", t)
        print("  %-24s konachan %-30s -> %d" % (name, t, len(got)), flush=True)
        pool += got
        if len(pool) >= 260:
            break
    if len(pool) < 80:
        for t in qtags[:3]:
            got = get("https://yande.re/post.json", t, pages=(1,))
            print("  %-24s yande    %-30s -> %d" % (name, t, len(got)), flush=True)
            pool += got
    seen, kept = set(), []
    pool.sort(key=lambda p: -(p["score"] or 0))
    for p in pool:
        k = (p["site"], str(p["id"]))
        if k in seen:
            continue
        seen.add(k)
        w, h = p["w"], p["h"]
        if not w or not h or not p.get("url") or not p.get("prev"):
            continue
        r = h / w
        if r < 1.15:           # phone wallpapers must be portrait
            continue
        if h < 1200 or w < 640:
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
        time.sleep(0.15)
    print("   previews=%d" % n, flush=True)

json.dump(cands, open(os.path.join(OUT, "cands2.json"), "w"), indent=1)

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
print("SUMMARY", json.dumps(summary, indent=1), flush=True)
