#!/usr/bin/env python3
"""Lowrun18 stage 1: fetch candidates + contact sheets."""
import io, json, os, re, time
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
      "Referer": "https://konachan.net/"}
SERIES = [
    ("initial d", ["initial_d"]),
    ("ponyo", ["gake_no_ue_no_ponyo", "ponyo"]),
    ("apothecary diaries", ["kusuriya_no_hitorigoto"]),
    ("nausicaa", ["kaze_no_tani_no_nausicaa", "nausicaa"]),
    ("howls moving castle", ["howl_no_ugoku_shiro"]),
    ("seven deadly sins", ["nanatsu_no_taizai"]),
    ("girls band cry", ["girls_band_cry"]),
    ("detective conan", ["detective_conan"]),
    ("eminence in shadow", ["kage_no_jitsuryokusha_ni_naritakute!"]),
    ("haikyuu", ["haikyuu!!"]),
]
BAD = set("""text english_text watermark signature artist_name speech_bubble comic 4koma multiple_views
character_sheet translated logo border frame letterboxed twitter_username web_address dated artist_logo
english_commentary bad_id sketch monochrome greyscale partially_colored censored manga scan sample food
chibi comic_panel bikini swimsuit underwear lingerie panties bra cleavage no_bra see_through spread_legs
large_breasts huge_breasts nude naked topless wet bed bottomless sideboob underboob photo photograph
cosplay screencap screenshot reference_sheet upscaled jpeg_artifacts lowres real_world_location
photo_background collage crossover vector lineart line_art blood gore guro game_cg cgi anime_screencap
screen_capture redraw official_art promotional_art key_visual poster banner album cover movie_poster
bad_pixiv_id commentary commentary_request translation_request character_request artist_request
wide_image phone_wallpaper variant_set resolution_mismatch partially_translated chinese_text korean_text
japanese_text loli child aged_down muscular abs sweat tongue pov faceless_male male_focus greeting_card
calendar sticker meme logo_parody parody fake_screenshot photo_manipulation real_photo""".split())

OUT = "_tmp/lowrun18"
PREV, SHEETS = OUT + "/prev", OUT + "/sheets"
os.makedirs(PREV, exist_ok=True)
os.makedirs(SHEETS, exist_ok=True)
PER_SERIES = 22


def render(im, size=(360, 640)):
    w, h = im.size
    tw, th = size
    t = 16 / 9
    if h / w > 2.2:
        bg = ImageOps.fit(im, (tw, th), Image.LANCZOS).filter(ImageFilter.GaussianBlur(22))
        fg = im.copy()
        fg.thumbnail((tw, th), Image.LANCZOS)
        bg.paste(fg, ((tw - fg.width) // 2, (th - fg.height) // 2))
        return bg
    if h / w > t:
        nh = int(w * t)
        y = int((h - nh) * 0.04)
        return im.crop((0, y, w, y + nh))
    nw = int(h / t)
    x = (w - nw) // 2
    return im.crop((x, 0, x + nw, h))


def get(url, params):
    for _ in range(3):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=40)
            if r.status_code == 200:
                time.sleep(0.8)
                return r
            print("  HTTP", r.status_code, flush=True)
        except Exception as e:
            print("  ERR", type(e).__name__, flush=True)
        time.sleep(4)


def fetch_site(base, tag):
    out = []
    for page in (1, 2):
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
                            w=p.get("width") or 0, h=p.get("height") or 0, url=p.get("file_url"),
                            prev=p.get("sample_url") or p.get("jpeg_url") or p.get("file_url"),
                            tags=p.get("tags") or "", rating=p.get("rating")))
        if len(js) < 100:
            break
    return out


used = set()
for f in ("_tmp/lowrun15/used_pids.json", "_tmp/lowrun16/used_pids.json",
          "_tmp/lowrun17/used_pids.json", OUT + "/used_pids.json"):
    if os.path.exists(f):
        try:
            used |= set(str(x) for x in json.load(open(f)))
        except Exception:
            pass
print("used pids:", len(used), flush=True)

cands = []
for name, tags in SERIES:
    pool = []
    for t in tags:
        got = fetch_site("https://konachan.net/post.json", t)
        print("  %s %s -> %d" % (name, t, len(got)), flush=True)
        pool += got
        if len(pool) >= 200:
            break
    if len(pool) < 60:
        for t in tags:
            pool += fetch_site("https://yande.re/post.json", t)
    print("== %s pool=%d" % (name, len(pool)), flush=True)
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
            render(im).save("%s/%s_%02d.jpg" % (PREV, slug, n), "JPEG", quality=84, optimize=True)
            cands.append(dict(series=name, slug=slug, idx=n, file="%s_%02d.jpg" % (slug, n), pid=p["id"],
                              site=p["site"], score=p["score"], w=p["w"], h=p["h"], url=p["url"],
                              tags=p["tags"][:400]))
            n += 1
        except Exception as e:
            print("   dl err", p.get("id"), type(e).__name__, flush=True)
        time.sleep(0.2)
    print("   previews=%d" % n, flush=True)

json.dump(cands, open(OUT + "/cands.json", "w"), indent=1)

COLS, ROWS, CW, CH = 5, 5, 300, 533
per = COLS * ROWS
bys = {}
for c in cands:
    bys.setdefault(c["slug"], []).append(c)
for slug, items in bys.items():
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
        sheet.save("%s/%s_%d.jpg" % (SHEETS, slug, si // per), "JPEG", quality=86, optimize=True)

print("TOTAL", len(cands), flush=True)
print("sheets", sorted(os.listdir(SHEETS)), flush=True)
