#!/usr/bin/env python3
"""Low-count run (05:00 IST, 2026-11-16) stage 1b: wider fetch, relaxed size filters."""
import io, json, os, re, time
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json,text/plain,*/*",
      "Referer": "https://konachan.net/"}

# (display name, konachan/yande tags)
SERIES = [
    ("initial d",                    ["initial_d"]),
    ("the promised neverland",       ["yakusoku_no_neverland", "the_promised_neverland"]),
    ("anohana",                      ["anohana", "anohana:_the_flower_we_saw_that_day", "menma_(anohana)"]),
    ("overlord",                     ["overlord_(maruyama)", "overlord"]),
    ("weathering with you",          ["tenki_no_ko"]),
    ("detective conan",              ["detective_conan", "case_closed"]),
    ("mahou shoujo madoka magica",   ["mahou_shoujo_madoka_magica"]),
    ("psycho pass",                  ["psycho-pass", "psycho_pass"]),
    ("kaze no tani no nausicaa",     ["kaze_no_tani_no_nausicaa", "nausicaa"]),
    ("haikyuu",                      ["haikyuu!!", "haikyuu"]),
    ("lycoris recoil",               ["lycoris_recoil"]),
    ("tokyo revengers",              ["tokyo_revengers"]),
]

BAD = {"text", "english_text", "watermark", "signature", "artist_name", "speech_bubble", "comic", "4koma",
       "multiple_views", "character_sheet", "translated", "logo", "border", "frame", "letterboxed",
       "twitter_username", "web_address", "dated", "artist_logo", "english_commentary", "bad_id",
       "sketch", "monochrome", "greyscale", "partially_colored", "censored", "manga", "scan", "sample",
       "chibi", "comic_panel", "bikini", "swimsuit", "underwear", "lingerie", "panties", "bra",
       "cleavage", "no_bra", "see_through", "spread_legs", "large_breasts", "huge_breasts",
       "nude", "naked", "topless", "wet", "bed", "bottomless", "sideboob", "underboob", "photo",
       "photograph", "cosplay", "screencap", "screenshot", "reference_sheet", "jpeg_artifacts",
       "lowres", "real_world_location", "photo_background", "collage", "crossover", "vector",
       "lineart", "line_art", "blood", "gore", "guro", "game_cg", "cgi", "anime_screencap",
       "screen_capture", "redraw", "movie_poster", "bad_pixiv_id", "commentary", "commentary_request",
       "translation_request", "character_request", "artist_request", "variant_set",
       "resolution_mismatch", "chinese_text", "korean_text", "japanese_text", "loli",
       "aged_down", "pov", "faceless_male", "male_focus", "poll", "comic_page", "animated_gif",
       "ugoira", "third-party_edit", "revision", "bad_link", "partially_translated"}

OUT = "_tmp/lowrun16"
PREV = os.path.join(OUT, "prev")
SHEETS = os.path.join(OUT, "sheets")
os.makedirs(PREV, exist_ok=True)
os.makedirs(SHEETS, exist_ok=True)

CAP = 30


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


def get(url, params, timeout=90):
    for _ in range(2):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout)
            if r.status_code == 200:
                time.sleep(1.2)
                return r
            print("  HTTP", r.status_code, url, flush=True)
        except Exception as e:
            print("  ERR", type(e).__name__, flush=True)
        time.sleep(3)
    return None


def fetch_site(base, tag):
    r = get(base, {"tags": tag + " rating:s", "limit": 100, "page": 1})
    if not r:
        return []
    try:
        js = r.json()
    except Exception:
        return []
    if not isinstance(js, list):
        return []
    out = []
    for p in js:
        out.append(dict(site=base, id=p.get("id"), score=p.get("score") or 0,
                        w=p.get("width") or 0, h=p.get("height") or 0,
                        url=p.get("file_url"),
                        prev=p.get("sample_url") or p.get("jpeg_url") or p.get("file_url"),
                        tags=p.get("tags") or "", rating=p.get("rating")))
    return out


used = set()
uf = os.path.join(OUT, "used_pids.json")
if os.path.exists(uf):
    used = set(str(x) for x in json.load(open(uf)))

cands = []
cf = os.path.join(OUT, "cands.json")
if os.path.exists(cf):
    cands = json.load(open(cf))
have = {}
for c in cands:
    have.setdefault(c["series"], []).append(c)
print("existing cands:", {k: len(v) for k, v in have.items()}, flush=True)
print("used pids:", len(used), flush=True)

for name, tags in SERIES:
    cur = have.get(name, [])
    if len(cur) >= CAP:
        print("== %s already %d" % (name, len(cur)), flush=True)
        continue
    pool = []
    for t in tags:
        got = fetch_site("https://konachan.net/post.json", t)
        print("  %s konachan %s -> %d" % (name, t, len(got)), flush=True)
        pool += got
        if len(pool) >= 120:
            break
    if len(pool) < 40:
        for t in tags:
            got = fetch_site("https://yande.re/post.json", t)
            print("  %s yande %s -> %d" % (name, t, len(got)), flush=True)
            pool += got
    print("== %s pool=%d" % (name, len(pool)), flush=True)

    seen = set(str(c["pid"]) for c in cur)
    kept = []
    pool.sort(key=lambda p: -(p["score"] or 0))
    for p in pool:
        pid = str(p["id"])
        if pid in seen or pid in used:
            continue
        seen.add(pid)
        w, h = p["w"], p["h"]
        if not w or not h or not p.get("url") or not p.get("prev"):
            continue
        r = h / w
        if r >= 1.2:
            if h < 1150 or w < 600:
                continue
        elif r >= 0.85:
            if h < 1350:
                continue
        else:
            if h < 1080 or w < 1600:
                continue
        if set(p["tags"].split()) & BAD:
            continue
        if p.get("rating") not in ("s", None):
            continue
        kept.append(p)
    print("   new valid=%d" % len(kept), flush=True)

    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    n = max([c["idx"] for c in cur]) + 1 if cur else 0
    added = 0
    for p in kept:
        if len(cur) + added >= CAP:
            break
        try:
            r = requests.get(p["prev"], headers=UA, timeout=90)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            fn = "%s_%02d.jpg" % (slug, n)
            render(im).save(os.path.join(PREV, fn), "JPEG", quality=84, optimize=True)
            cands.append(dict(series=name, slug=slug, idx=n, file=fn, pid=p["id"], site=p["site"],
                              score=p["score"], w=p["w"], h=p["h"], url=p["url"], tags=p["tags"][:400]))
            n += 1
            added += 1
        except Exception as e:
            print("   dl err", p.get("id"), type(e).__name__, flush=True)
        time.sleep(0.15)
    print("   previews+=%d (total %d)" % (added, len(cur) + added), flush=True)

json.dump(cands, open(cf, "w"), indent=1)

for f in os.listdir(SHEETS):
    os.remove(os.path.join(SHEETS, f))
COLS, ROWS = 5, 4
CW, CH = 300, 533
per = COLS * ROWS
byseries = {}
for c in cands:
    byseries.setdefault(c["slug"], []).append(c)
for slug, items in byseries.items():
    items.sort(key=lambda c: c["idx"])
    for si in range(0, len(items), per):
        chunk = items[si:si + per]
        sheet = Image.new("RGB", (COLS * CW, ROWS * CH), (18, 18, 18))
        dr = ImageDraw.Draw(sheet)
        for k, c in enumerate(chunk):
            p = os.path.join(PREV, c["file"])
            if not os.path.exists(p):
                continue
            im = Image.open(p).convert("RGB").resize((CW, CH), Image.LANCZOS)
            x, y = (k % COLS) * CW, (k // COLS) * CH
            sheet.paste(im, (x, y))
            dr.rectangle([x, y, x + 34, y + 20], fill=(0, 0, 0))
            dr.text((x + 5, y + 5), str(c["idx"]), fill=(255, 255, 0))
        sheet.save(os.path.join(SHEETS, "%s_%d.jpg" % (slug, si // per)), "JPEG", quality=86, optimize=True)

print("TOTAL candidates", len(cands), flush=True)
print("sheets:", len(os.listdir(SHEETS)), flush=True)
