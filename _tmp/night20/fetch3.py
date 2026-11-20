#!/usr/bin/env python3
"""Night gap-fill round 3: wallhaven primary, danbooru/konachan fallback."""
import io, json, os, re, time
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json,text/plain,*/*"}

# display name -> wallhaven queries, danbooru tag, konachan tag
SERIES = [
    ("fruits basket", ["fruits basket", "tohru honda", "kyo sohma"], "fruits_basket", "fruits_basket"),
    ("tower of god", ["tower of god", "twenty fifth bam"], "tower_of_god", "tower_of_god"),
    ("the ancient magus bride", ["ancient magus bride", "chise hatori"], "mahou_tsukai_no_yome", "mahou_tsukai_no_yome"),
    ("bungou stray dogs", ["bungou stray dogs", "stray dogs dazai"], "bungou_stray_dogs", "bungou_stray_dogs"),
    ("nichijou", ["nichijou"], "nichijou", "nichijou"),
    ("shokugeki no soma", ["food wars", "shokugeki no soma"], "shokugeki_no_souma", "shokugeki_no_souma"),
    ("danmachi", ["danmachi", "is it wrong to try to pick up girls in a dungeon"], "dungeon_ni_deai_wo_motomeru_no_wa_machigatteiru_darou_ka", "danmachi"),
    ("sakurasou", ["sakurasou", "pet girl of sakurasou"], "sakurasou_no_pet_na_kanojo", "sakurasou_no_pet_na_kanojo"),
    ("ouran host club", ["ouran high school host club"], "ouran_high_school_host_club", "ouran_koukou_host_club"),
    ("love live", ["love live school idol project", "love live"], "love_live!", "love_live!"),
    ("zombieland saga", ["zombieland saga"], "zombieland_saga", "zombieland_saga"),
    ("another", ["another misaki mei"], "another_(anime)", "another"),
    ("parasyte", ["parasyte", "kiseijuu"], "kiseijuu", "kiseijuu"),
    ("march comes in like a lion", ["march comes in like a lion"], "3-gatsu_no_lion", "3-gatsu_no_lion"),
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
       "anime_screencap", "screen_capture", "redraw", "pantyhose", "loli", "child", "3d",
       "muscular", "male_focus"}

OUT = "_tmp/night20"
PREV = os.path.join(OUT, "prev3")
SHEETS = os.path.join(OUT, "sheets3")
os.makedirs(PREV, exist_ok=True)
os.makedirs(SHEETS, exist_ok=True)
PER_SERIES = 12
MAX_SERIES = 7


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


def get(url, params, timeout=25):
    try:
        r = requests.get(url, params=params, headers=UA, timeout=timeout)
        print("   HTTP", r.status_code, url.split("?")[0], flush=True)
        if r.status_code == 200:
            return r
    except Exception as e:
        print("   ERR", type(e).__name__, url.split("?")[0], flush=True)
    return None


def wallhaven(q):
    r = get("https://wallhaven.cc/api/v1/search",
            {"q": q, "categories": "010", "purity": "100", "sorting": "relevance",
             "order": "desc", "atleast": "1000x1400", "page": 1})
    out = []
    if not r:
        return out
    try:
        js = r.json()
    except Exception:
        return out
    for p in js.get("data", []):
        w = p.get("dimension_x") or 0
        h = p.get("dimension_y") or 0
        out.append(dict(site="wallhaven", id=p.get("id"), score=0, w=w, h=h,
                        url=p.get("path"), prev=p.get("path"),
                        tags=" ".join(t.get("name", "") for t in (p.get("tags") or [])), rating="s"))
    return out


def danbooru(tag):
    r = get("https://danbooru.donmai.us/posts.json",
            {"tags": tag + " rating:general order:score", "limit": 60, "page": 1})
    out = []
    if not r:
        return out
    try:
        js = r.json()
    except Exception:
        return out
    for p in js or []:
        out.append(dict(site="danbooru", id=p.get("id"), score=p.get("score") or 0,
                        w=p.get("image_width") or 0, h=p.get("image_height") or 0,
                        url=p.get("file_url"),
                        prev=p.get("large_file_url") or p.get("preview_file_url") or p.get("file_url"),
                        tags=p.get("tag_string") or "", rating="s"))
    return out


def konachan(tag):
    r = get("https://konachan.net/post.json", {"tags": tag + " rating:s", "limit": 100, "page": 1})
    out = []
    if not r:
        return out
    try:
        js = r.json()
    except Exception:
        return out
    for p in js or []:
        out.append(dict(site="konachan", id=p.get("id"), score=p.get("score") or 0,
                        w=p.get("width") or 0, h=p.get("height") or 0,
                        url=p.get("file_url"),
                        prev=p.get("sample_url") or p.get("jpeg_url") or p.get("file_url"),
                        tags=p.get("tags") or "", rating=p.get("rating")))
    return out


def valid(p):
    w, h = p["w"], p["h"]
    if not w or not h or not p.get("url") or not p.get("prev"):
        return False
    r = h / w
    if r >= 1.15:
        if h < 1200 or w < 640:
            return False
    elif r <= 0.8:
        if w < 1500:
            return False
    else:
        return False
    if set(p["tags"].split()) & BAD:
        return False
    if p.get("rating") not in ("s", None):
        return False
    return True


probes, chosen = [], []
for name, wqs, dtag, ktag in SERIES:
    pool = []
    for q in wqs:
        got = wallhaven(q)
        print("  %s wallhaven '%s' -> %d" % (name, q, len(got)), flush=True)
        pool += got
        if len([p for p in pool if valid(p)]) >= 20:
            break
    if len([p for p in pool if valid(p)]) < 6:
        got = danbooru(dtag)
        print("  %s danbooru -> %d" % (name, len(got)), flush=True)
        pool += got
    if len([p for p in pool if valid(p)]) < 6:
        got = konachan(ktag)
        print("  %s konachan -> %d" % (name, len(got)), flush=True)
        pool += got
    seen, kept = set(), []
    for p in sorted([p for p in pool if valid(p)], key=lambda x: -(x["score"] or 0)):
        if p["url"] in seen:
            continue
        seen.add(p["url"])
        kept.append(p)
    print("== %s pool=%d valid=%d" % (name, len(pool), len(kept)), flush=True)
    probes.append((name, len(kept)))
    if len(kept) >= 6:
        chosen.append((name, kept))
    if len(chosen) >= MAX_SERIES:
        break
    time.sleep(1)

json.dump(probes, open(os.path.join(OUT, "probes3.json"), "w"), indent=1)
print("CHOSEN", [c[0] for c in chosen], flush=True)

cands = []
for name, pool in chosen:
    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    n = 0
    for p in pool:
        if n >= PER_SERIES:
            break
        try:
            r = requests.get(p["prev"], headers=UA, timeout=45)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            fn = "%s_%02d.jpg" % (slug, n)
            render(im).save(os.path.join(PREV, fn), "JPEG", quality=82, optimize=True)
            cands.append(dict(series=name, slug=slug, idx=n, pid="%s-%s" % (p["site"], p["id"]),
                              site=p["site"], score=p["score"], w=p["w"], h=p["h"], url=p["url"],
                              tags=p["tags"][:500]))
            n += 1
        except Exception as e:
            print("   dl err", p.get("id"), type(e).__name__, flush=True)
        time.sleep(0.2)
    print("   previews=%d %s" % (n, name), flush=True)

json.dump(cands, open(os.path.join(OUT, "cands3.json"), "w"), indent=1)

COLS, ROWS = 4, 3
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
