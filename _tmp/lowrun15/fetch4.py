#!/usr/bin/env python3
"""Low-count run (17:00 IST, 2026-11-15) stage 1d: wallhaven-first candidates."""
import io, json, os, re, time
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json,text/plain,*/*",
      "Referer": "https://konachan.com/"}

SERIES = [
    ("nanatsu no taizai", ["nanatsu_no_taizai", "meliodas", "elizabeth_liones", "escanor", "ban_(nanatsu_no_taizai)", "king_(nanatsu_no_taizai)", "diane_(nanatsu_no_taizai)", "merlin_(nanatsu_no_taizai)"]),
    ("kaiju no 8", ["kaijuu_8_gou", "hibino_kafka", "ashiro_mitsuki", "shinomiya_kikoru", "ichikawa_reno", "hoshina_soshiro"]),
    ("saga of tanya the evil", ["youjo_senki", "tanya_degurechaff", "viktoriya_ivanovna_serebryakova"]),
    ("girls band cry", ["girls_band_cry", "togenashi_togeari", "ishigaki_nina", "kawaragi_momoka"]),
    ("soul eater", ["soul_eater", "maka_albarn", "soul_eater_evans", "black_star", "death_the_kid", "tsubaki_nakatsukasa", "crona_(soul_eater)"]),
    ("berserk", ["berserk", "guts_(berserk)", "griffith_(berserk)", "casca_(berserk)", "schierke_(berserk)"]),
    ("dungeon meshi", ["dungeon_meshi", "laios_touden", "marcille_donato", "falin_touden", "izutsumi", "chilchuck_timz", "senshi_(dungeon_meshi)"]),
    ("hunter x hunter", ["hunter_x_hunter", "killua_zoldyck", "gon_freecss", "kurapika", "hisoka_morow", "leorio_paladiknight"]),
    ("fate/stay night", ["fate/stay_night", "saber_(fate)", "tohsaka_rin", "matou_sakura", "illyasviel_von_einzbern", "archer_(fate)", "rider_(fate/stay_night)"]),
    ("wind breaker", ["wind_breaker", "sakura_haruka", "suo_hayato", "nirei_akihiko", "bofurin"]),
]

WH_Q = {
    "nanatsu no taizai": ["seven deadly sins", "meliodas", "escanor", "elizabeth"],
    "kaiju no 8": ["kaiju no 8", "kaiju", "kikoru", "kafka"],
    "saga of tanya the evil": ["tanya", "youjo senki", "tanya degurechaff"],
    "girls band cry": ["girls band cry", "togenashi"],
    "soul eater": ["soul eater", "maka", "death the kid"],
    "berserk": ["berserk", "guts", "griffith"],
    "dungeon meshi": ["dungeon meshi", "laios", "marcille"],
    "hunter x hunter": ["hunter x hunter", "killua", "kurapika"],
    "fate/stay night": ["fate stay night", "saber", "rin tohsaka", "sakura matou"],
    "wind breaker": ["wind breaker", "sakura haruka"],
}

BAD = {"text", "english_text", "watermark", "signature", "artist_name", "speech_bubble", "comic", "4koma",
       "multiple_views", "character_sheet", "translated", "logo", "border", "frame", "letterboxed",
       "twitter_username", "web_address", "dated", "artist_logo", "english_commentary", "bad_id",
       "sketch", "monochrome", "greyscale", "partially_colored", "censored", "manga", "scan", "sample",
       "food", "chibi", "comic_panel", "bikini", "swimsuit", "underwear", "lingerie", "panties", "bra",
       "cleavage", "no_bra", "see_through", "spread_legs", "large_breasts", "huge_breasts", "ass",
       "nude", "naked", "topless", "wet", "bed", "bottomless", "sideboob", "underboob", "photo",
       "photograph", "cosplay", "screencap", "screenshot", "reference_sheet", "upscaled",
       "jpeg_artifacts", "lowres", "real_world_location", "photo_background", "collage", "crossover",
       "vector", "lineart", "line_art", "guro", "graphic_violence", "dismemberment", "amputee",
       "anime_screencap", "screen_capture", "redraw", "game_cg", "official_art", "key_visual",
       "promotional_art", "poster", "album", "cover", "logo", "wallpaper_(object)", "wide_image"}

OUT = "_tmp/lowrun15"
PREV = os.path.join(OUT, "prev4")
SHEETS = os.path.join(OUT, "sheets4")
os.makedirs(PREV, exist_ok=True)
os.makedirs(SHEETS, exist_ok=True)
PER_SERIES = 30
TARGET_POOL = 60

used = set()
for fn in ["used_pids.json"]:
    p = os.path.join(OUT, fn)
    if os.path.exists(p):
        try:
            used |= {str(x) for x in json.load(open(p))}
        except Exception:
            pass
for fn in ["cands.json", "cands2.json", "cands3.json"]:
    p = os.path.join(OUT, fn)
    if os.path.exists(p):
        try:
            for e in json.load(open(p)):
                used.add(str(e.get("pid", "")).split(":")[-1])
        except Exception:
            pass
print("used ids:", len(used), flush=True)


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
    nw = int(h * t)
    x = (w - nw) // 2
    return im.crop((x, 0, x + nw, h))


def get(url, params=None, timeout=30, tries=2):
    for _ in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout)
            if r.status_code == 200:
                return r
            print("  HTTP", r.status_code, url, flush=True)
        except Exception as e:
            print("  ERR", type(e).__name__, flush=True)
        time.sleep(2)
    return None


def konachan(tag):
    out = []
    for page in (1, 2):
        r = get("https://konachan.com/post.json", {"tags": tag + " rating:s", "limit": 100, "page": page})
        if not r:
            break
        try:
            js = r.json()
        except Exception:
            break
        if not isinstance(js, list) or not js:
            break
        for p in js:
            out.append(dict(site="konachan.com", id=p.get("id"), score=p.get("score") or 0,
                            w=p.get("width") or 0, h=p.get("height") or 0, url=p.get("file_url"),
                            prev=p.get("sample_url") or p.get("jpeg_url") or p.get("file_url"),
                            tags=p.get("tags") or "", rating=p.get("rating")))
        if len(js) < 100:
            break
        time.sleep(0.8)
    return out


def wallhaven(q):
    out = []
    for page in (1, 2):
        r = get("https://wallhaven.cc/api/v1/search",
                {"q": q, "purity": "100", "categories": "010", "page": page})
        if not r:
            break
        try:
            js = r.json()
        except Exception:
            break
        data = js.get("data") or []
        for p in data:
            out.append(dict(site="wallhaven", id=p.get("id"), score=p.get("favorites") or 0,
                            w=p.get("dimension_x") or 0, h=p.get("dimension_y") or 0,
                            url=p.get("path"), prev=p.get("thumbs", {}).get("large") or p.get("thumbs", {}).get("original") or p.get("path"),
                            tags=" ".join(t.get("name", "") for t in (p.get("tags") or [])),
                            rating="s"))
        if not js.get("meta", {}).get("last_page", 1) > page:
            break
        time.sleep(1.0)
    return out


cands = []
for name, tags in SERIES:
    pool = []
    for q in WH_Q.get(name, []):
        got = wallhaven(q)
        print("  %s | wallhaven '%s' -> %d" % (name, q, len(got)), flush=True)
        pool += got
        if len(pool) >= TARGET_POOL:
            break
    if len(pool) < TARGET_POOL:
        for t in tags:
            got = konachan(t)
            print("  %s | konachan '%s' -> %d" % (name, t, len(got)), flush=True)
            pool += got
            if len(pool) >= TARGET_POOL:
                break
    print("== %s pool=%d" % (name, len(pool)), flush=True)

    seen, kept = set(), []
    pool.sort(key=lambda p: -(p["score"] or 0))
    for p in pool:
        key = str(p["id"])
        if key in seen or key in used:
            continue
        seen.add(key)
        w, h = p["w"], p["h"]
        if not w or not h or not p.get("url"):
            continue
        r = h / w
        if r >= 1.15:
            if h < 1300 or w < 700:
                continue
        elif r <= 0.85:
            if w < 2200:
                continue
        else:
            continue
        if set((p.get("tags") or "").split()) & BAD:
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
            r = requests.get(p["prev"], headers=UA, timeout=45)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            if min(im.size) < 260:
                continue
            fn = "%s_%02d.jpg" % (slug, n)
            render(im).save(os.path.join(PREV, fn), "JPEG", quality=82, optimize=True)
            cands.append(dict(series=name, slug=slug, idx=n, file=fn, pid="%s:%s" % (p["site"], p["id"]),
                              site=p["site"], score=p["score"], w=p["w"], h=p["h"], url=p["url"],
                              tags=p["tags"][:400]))
            n += 1
        except Exception as e:
            print("   dl err", p.get("id"), type(e).__name__, flush=True)
        time.sleep(0.15)
    print("   previews=%d" % n, flush=True)

json.dump(cands, open(os.path.join(OUT, "cands4.json"), "w"), indent=1)

COLS, ROWS = 5, 4
CW, CH = 240, 427
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
            dr.rectangle([x, y, x + 30, y + 18], fill=(0, 0, 0))
            dr.text((x + 4, y + 4), str(c["idx"]), fill=(255, 255, 0))
        sheet.save(os.path.join(SHEETS, "%s_%d.jpg" % (slug, si // per)), "JPEG", quality=88, optimize=True)

print("TOTAL candidates", len(cands), flush=True)
print("sheets:", len(os.listdir(SHEETS)), flush=True)
