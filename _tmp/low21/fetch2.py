#!/usr/bin/env python3
"""Low21 round 2: danbooru (rating:general) for series konachan could not cover."""
import io, json, os, re, time
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": "AniPixBot/1.0 (wallpaper curation; contact nobelfamily537@gmail.com)",
      "Accept": "application/json"}

SERIES = [
    ("the promised neverland", ["yakusoku_no_neverland"]),
    ("noir", ["noir_(anime)", "mireille_bouquet", "kirika_yuumura"]),
    ("fire force", ["enen_no_shouboutai"]),
    ("horimiya", ["horimiya", "hori_kyouko"]),
    ("kuroko no basket", ["kuroko_no_basket"]),
    ("natsume yuujinchou", ["natsume_yuujinchou"]),
    ("rent a girlfriend", ["kanojo_okarishimasu"]),
    ("dr stone", ["dr._stone"]),
    ("mob psycho 100", ["mob_psycho_100"]),
    ("mashle", ["mashle", "mash_burnedead"]),
    ("hollow knight", ["hollow_knight"]),
    ("minecraft", ["minecraft"]),
    ("sonic", ["sonic_the_hedgehog"]),
    ("from up on poppy hill", ["kokuriko-zaka_kara"]),
    ("the cat returns", ["neko_no_onggaeshi"]),
    ("the wind rises", ["kaze_tachinu"]),
    ("porco rosso", ["kurenai_no_buta"]),
    ("castle in the sky", ["tenkuu_no_shiro_laputa"]),
    ("tales from earthsea", ["gedo_senki"]),
]

BAD = {"text", "english_text", "translation_request", "translated", "commentary", "commentary_request",
       "watermark", "signature", "logo", "speech_bubble", "comic", "4koma", "multiple_views",
       "character_sheet", "sketch", "monochrome", "greyscale", "lineart", "chibi", "sample",
       "web_address", "twitter_username", "dated", "real_world_photo", "photo_(medium)", "cosplay",
       "screencap", "game_cg", "cgi", "lowres", "bad_id", "crossover", "parody", "meme", "pixel_art",
       "3d", "border", "letterboxed", "framed", "collage", "reference_sheet", "artist_name",
       "wallpaper_(medium)", "upscaled", "jpeg_artifacts", "compass", "diagram", "map", "chart",
       "nude", "naked", "topless", "underwear", "panties", "bra", "bikini", "swimsuit", "lingerie",
       "cleavage", "no_bra", "see_through", "bottomless", "spread_legs", "ass", "large_breasts",
       "huge_breasts", "sideboob", "underboob", "wet", "bed", "loli", "child", "blood", "gore"}

OUT = "_tmp/low21"
PREV = os.path.join(OUT, "prev2")
SHEETS = os.path.join(OUT, "sheets2")
os.makedirs(PREV, exist_ok=True)
os.makedirs(SHEETS, exist_ok=True)
PER_SERIES = 18


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


def get(url, params, tries=3):
    for a in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=40)
            if r.status_code == 200:
                time.sleep(0.6)
                return r
            print("  HTTP", r.status_code, flush=True)
            if r.status_code in (429, 503, 502):
                time.sleep(6 + 4 * a)
                continue
            if r.status_code == 403:
                time.sleep(4)
                continue
        except Exception as e:
            print("  ERR", type(e).__name__, flush=True)
        time.sleep(3)
    return None


def danbooru(tag):
    out = []
    for page in (1, 2):
        r = get("https://danbooru.donmai.us/posts.json",
                {"tags": "%s rating:general" % tag, "limit": 100, "page": page})
        if not r:
            break
        try:
            js = r.json()
        except Exception:
            break
        if not isinstance(js, list) or not js:
            break
        for p in js:
            out.append(dict(site="db", id="d" + str(p.get("id")), score=p.get("score") or 0,
                            w=p.get("image_width") or 0, h=p.get("image_height") or 0,
                            url=p.get("file_url"), prev=p.get("sample_url") or p.get("preview_file_url") or p.get("file_url"),
                            tags=p.get("tag_string") or "", rating="s"))
        if len(js) < 100:
            break
    return out


used = set()
for root, _, files in os.walk("_tmp"):
    for fn in files:
        if not fn.endswith(".json"):
            continue
        try:
            js = json.load(open(os.path.join(root, fn)))
        except Exception:
            continue
        for e in (js if isinstance(js, list) else []):
            if isinstance(e, dict) and "pid" in e:
                used.add(e["pid"])
print("used pids", len(used), flush=True)

cands = []
for name, queries in SERIES:
    pool, seen = [], set()
    for t in queries:
        got = danbooru(t)
        print("  %s %r -> %d" % (name, t, len(got)), flush=True)
        for p in got:
            if p["id"] not in seen:
                seen.add(p["id"])
                pool.append(p)
    print("== %s pool=%d" % (name, len(pool)), flush=True)
    kept = []
    for p in pool:
        if p["id"] in used:
            continue
        w, h = p["w"], p["h"]
        if not w or not h or not p.get("url") or not p.get("prev"):
            continue
        r = h / w
        if r >= 1.2:
            if h < 1100 or w < 550:
                continue
        elif r <= 0.8:
            if w < 1600 or h < 900:
                continue
        else:
            continue
        if set(p["tags"].split()) & BAD:
            continue
        kept.append(p)
    kept.sort(key=lambda p: (0 if (p["h"] / p["w"]) >= 1.2 else 1, -(p["score"] or 0)))
    print("   valid=%d portrait=%d" % (len(kept), sum(1 for p in kept if p["h"] / p["w"] >= 1.2)), flush=True)
    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    n = 0
    for p in kept:
        if n >= PER_SERIES:
            break
        ok, im = False, None
        for a in range(2):
            try:
                r = requests.get(p["prev"], headers=UA, timeout=45)
                r.raise_for_status()
                im = Image.open(io.BytesIO(r.content)).convert("RGB")
                ok = True
                break
            except Exception as e:
                print("   dl err", p["id"], type(e).__name__, flush=True)
                time.sleep(2)
        if not ok:
            continue
        fn = "%s_%02d.jpg" % (slug, n)
        render(im).save(os.path.join(PREV, fn), "JPEG", quality=82, optimize=True)
        cands.append(dict(series=name, slug=slug, idx=n, file=fn, pid=p["id"], site="db",
                          score=p["score"], w=p["w"], h=p["h"], url=p["url"], tags=p["tags"][:500]))
        n += 1
    print("   previews=%d" % n, flush=True)

json.dump(cands, open(os.path.join(OUT, "cands2.json"), "w"), indent=1)

COLS, ROWS = 5, 4
CW, CH = 240, 427
by = {}
for c in cands:
    by.setdefault(c["slug"], []).append(c)
for slug, items in by.items():
    for si in range(0, len(items), COLS * ROWS):
        chunk = items[si:si + COLS * ROWS]
        sheet = Image.new("RGB", (COLS * CW, ROWS * CH), (18, 18, 18))
        dr = ImageDraw.Draw(sheet)
        for k, c in enumerate(chunk):
            im = Image.open(os.path.join(PREV, c["file"])).convert("RGB").resize((CW, CH), Image.LANCZOS)
            x, y = (k % COLS) * CW, (k // COLS) * CH
            sheet.paste(im, (x, y))
            dr.rectangle([x, y, x + 30, y + 18], fill=(0, 0, 0))
            dr.text((x + 4, y + 4), str(c["idx"]), fill=(255, 255, 0))
        sheet.save(os.path.join(SHEETS, "%s_%d.jpg" % (slug, si // COLS * ROWS)), "JPEG", quality=88, optimize=True)
print("TOTAL", len(cands), flush=True)
