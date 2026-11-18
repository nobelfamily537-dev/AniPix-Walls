#!/usr/bin/env python3
"""Low-count run 2026-11-18 17:00 IST: candidates for the emptiest series tags.
Sources: konachan.net + yande.re (Pixiv art), safebooru for game IPs. Portrait-first."""
import io, json, os, re, time
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json,text/plain,*/*"}

SERIES = [
    ("digimon", ["digimon", "digimon_adventure", "agumon", "gabumon", "patamon"], "b"),
    ("from up on poppy hill", ["kokuriko_zaka_kara", "ghibli", "matsuzaki_umi"], "k"),
    ("hollow knight", ["hollow_knight", "hornet_(hollow_knight)"], "s"),
    ("no game no life", ["no_game_no_life"], "b"),
    ("the cat returns", ["neko_no_onggaeshi", "baron_humbert_von_gikkingen", "ghibli"], "k"),
    ("the promised neverland", ["yakusoku_no_neverland"], "b"),
    ("the wind rises", ["kaze_tachinu", "ghibli", "naoko_satomi"], "k"),
    ("mario", ["mario", "super_mario", "princess_peach", "rosalina"], "s"),
    ("minecraft", ["minecraft"], "s"),
    ("noir", ["noir", "mireille_bouquet", "kirika_yuumura"], "k"),
    ("sonic", ["sonic_the_hedgehog", "sonic", "amy_rose"], "s"),
    ("fire force", ["enen_no_shouboutai"], "b"),
    ("horimiya", ["horimiya", "hori_kyouko", "miyamura_izumi"], "b"),
    ("kuroko no basket", ["kuroko_no_basket"], "b"),
    ("natsume yuujinchou", ["natsume_yuujinchou", "natsume_takashi"], "b"),
    ("porco rosso", ["kurenai_no_buta", "ghibli"], "k"),
    ("tales from earthsea", ["gedo_senki", "ghibli"], "k"),
    ("made in abyss", ["made_in_abyss"], "b"),
    ("mashle", ["mashle", "mash_burnedead"], "b"),
    ("rent a girlfriend", ["kanojo_okarishimasu"], "b"),
    ("dr stone", ["dr_stone"], "b"),
    ("mob psycho 100", ["mob_psyco_100"], "b"),
    ("castle in the sky", ["tenkuu_no_shiro_laputa", "ghibli"], "k"),
    ("spirited away", ["sen_to_chihiro_no_kamikakushi", "ghibli"], "k"),
]

BADTAGS = {"text", "english_text", "watermark", "signature", "artist_name", "speech_bubble", "comic",
           "4koma", "multiple_views", "character_sheet", "translated", "logo", "border", "frame",
           "letterboxed", "twitter_username", "web_address", "dated", "artist_logo", "bad_id",
           "sketch", "monochrome", "greyscale", "partially_colored", "censored", "manga", "scan",
           "sample", "chibi", "comic_panel", "bikini", "swimsuit", "underwear", "lingerie", "panties",
           "bra", "cleavage", "no_bra", "see_through", "nude", "naked", "topless", "bed", "bottomless",
           "photo", "photograph", "cosplay", "screencap", "screenshot", "reference_sheet", "upscaled",
           "jpeg_artifacts", "lowres", "real_world_location", "photo_background", "collage", "crossover",
           "vector", "lineart", "line_art", "blood", "gore", "guro", "game_cg", "cgi", "redraw",
           "loli", "child", "close-up", "eyes", "pantyhose", "spread_legs", "ass", "large_breasts",
           "huge_breasts", "sideboob", "underboob", "wet", "meme", "parody", "pixel_art", "3d",
           "blender", "screenshot", "map", "diagram", "chart", "ui", "interface", "stats",
           "screencap", "poster", "cover", "album_cover", "dvd_cover", "wallpaper_(medium)"}

OUT = "_tmp/low21"
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


def get(url, params=None, timeout=30, tries=3, referer=None):
    hdr = dict(UA)
    if referer:
        hdr["Referer"] = referer
    for attempt in range(tries):
        try:
            r = requests.get(url, params=params, headers=hdr, timeout=timeout)
            if r.status_code == 200:
                time.sleep(0.5)
                return r
            print("  HTTP", r.status_code, url, flush=True)
            if r.status_code in (403, 429, 503):
                time.sleep(8 + 4 * attempt)
                continue
        except Exception as e:
            print("  ERR", type(e).__name__, flush=True)
        time.sleep(2)
    return None


def board_search(site, tag):
    out = []
    if site == "k":
        base, ref, extra = "https://konachan.net/post.json", "https://konachan.net/", " rating:s"
    elif site == "y":
        base, ref, extra = "https://yande.re/post.json", "https://yande.re/", " rating:s"
    else:
        base, ref, extra = "https://safebooru.donmai.us/posts.json", "https://safebooru.donmai.us/", ""
    for page in (1, 2):
        params = {"tags": tag + extra, "limit": 100, "page": page}
        r = get(base, params, referer=ref)
        if not r:
            break
        try:
            js = r.json()
        except Exception:
            break
        if not isinstance(js, list) or not js:
            break
        for p in js:
            if site == "s":
                out.append(dict(site="safe", id="s" + str(p.get("id")), score=p.get("score") or 0,
                                w=p.get("image_width") or 0, h=p.get("image_height") or 0,
                                url=p.get("file_url"), prev=p.get("sample_file_url") or p.get("preview_file_url") or p.get("file_url"),
                                tags=p.get("tag_string") or "", rating="s"))
            else:
                out.append(dict(site=site, id=site + str(p.get("id")), score=p.get("score") or 0,
                                w=p.get("width") or 0, h=p.get("height") or 0,
                                url=p.get("file_url"), prev=p.get("sample_url") or p.get("jpeg_url") or p.get("file_url"),
                                tags=p.get("tags") or "", rating=p.get("rating")))
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
print("already-used pids:", len(used), flush=True)

cands = []
for name, queries, sites in SERIES:
    pool, seen = [], set()
    for t in queries:
        for site in ("k", "y") if sites == "b" else ("k",) if sites == "k" else ("s", "k"):
            got = board_search(site, t)
            print("  %s %s %r -> %d" % (name, site, t, len(got)), flush=True)
            for p in got:
                if p["id"] not in seen:
                    seen.add(p["id"])
                    pool.append(p)
    print("== %s: pool=%d" % (name, len(pool)), flush=True)

    kept = []
    for p in pool:
        if p["id"] in used:
            continue
        w, h = p["w"], p["h"]
        if not w or not h or not p.get("url") or not p.get("prev"):
            continue
        r = h / w
        if r >= 1.2:
            if h < 1200 or w < 600:
                continue
        elif r <= 0.8:
            if w < 1900:
                continue
        else:
            continue
        if set(p["tags"].split()) & BADTAGS:
            continue
        if p.get("rating") not in ("s", None):
            continue
        kept.append(p)
    kept.sort(key=lambda p: (0 if (p["h"] / p["w"]) >= 1.2 else 1, -(p["score"] or 0)))
    print("   valid=%d (portrait=%d)" % (len(kept), sum(1 for p in kept if p["h"] / p["w"] >= 1.2)), flush=True)

    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    n = 0
    for p in kept:
        if n >= PER_SERIES:
            break
        ok, im = False, None
        ref = {"k": "https://konachan.net/", "y": "https://yande.re/", "safe": "https://safebooru.donmai.us/"}[p["site"]]
        for attempt in range(2):
            try:
                hdr = dict(UA)
                hdr["Referer"] = ref
                r = requests.get(p["prev"], headers=hdr, timeout=40)
                r.raise_for_status()
                im = Image.open(io.BytesIO(r.content)).convert("RGB")
                ok = True
                break
            except Exception as e:
                print("   dl err", p.get("id"), type(e).__name__, flush=True)
                time.sleep(2)
        if not ok:
            continue
        fn = "%s_%02d.jpg" % (slug, n)
        render(im).save(os.path.join(PREV, fn), "JPEG", quality=82, optimize=True)
        cands.append(dict(series=name, slug=slug, idx=n, file=fn, pid=p["id"], site=p["site"],
                          score=p["score"], w=p["w"], h=p["h"], url=p["url"], tags=p["tags"][:400]))
        n += 1
        time.sleep(0.15)
    print("   previews=%d" % n, flush=True)

json.dump(cands, open(os.path.join(OUT, "cands.json"), "w"), indent=1)

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
print("sheets:", sorted(os.listdir(SHEETS)), flush=True)
