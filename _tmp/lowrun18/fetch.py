#!/usr/bin/env python3
"""Lowrun18 stage 1 (v3): fetch candidates from safebooru.org + wallhaven + contact sheets."""
import io, json, os, re, time
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"}
SERIES = [
    ("initial d", ["initial_d", "initial_d_(anime)"]),
    ("ponyo", ["gake_no_ue_no_ponyo"]),
    ("apothecary diaries", ["kusuriya_no_hitorigoto", "maomao_(kusuriya_no_hitorigoto)"]),
    ("nausicaa", ["kaze_no_tani_no_nausicaa"]),
    ("howls moving castle", ["howl_no_ugoku_shiro"]),
    ("seven deadly sins", ["nanatsu_no_taizai"]),
    ("girls band cry", ["girls_band_cry", "girls_band_cry_(anime)"]),
    ("detective conan", ["detective_conan"]),
    ("eminence in shadow", ["kage_no_jitsuryokusha_ni_naritakute!", "eminence_in_shadow"]),
    ("haikyuu", ["haikyuu!!", "haikyuu"]),
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
calendar sticker meme logo_parody parody fake_screenshot photo_manipulation real_photo
english_text watermark_text""".split())

OUT = "_tmp/lowrun18"
PREV, SHEETS = OUT + "/prev", OUT + "/sheets"
os.makedirs(PREV, exist_ok=True)
os.makedirs(SHEETS, exist_ok=True)
PER_SERIES = 22
S = requests.Session()
S.headers.update(UA)


def get(url, params=None, tries=3, timeout=45):
    for k in range(tries):
        try:
            r = S.get(url, params=params, timeout=timeout)
            if r.status_code == 200:
                return r
            print("  HTTP", r.status_code, url.split("?")[0], flush=True)
        except Exception as e:
            print("  ERR", type(e).__name__, url.split("?")[0], flush=True)
        time.sleep(3 + 3 * k)
    return None


def sb_fetch(tag, pid):
    r = get("https://safebooru.org/index.php",
            {"page": "dapi", "s": "post", "q": "index", "json": "1", "limit": 100,
             "pid": pid, "tags": tag + " rating:safe"})
    if not r:
        return []
    try:
        js = r.json()
    except Exception:
        return []
    out = []
    for p in js if isinstance(js, list) else []:
        try:
            w, h = int(p.get("width") or 0), int(p.get("height") or 0)
        except Exception:
            continue
        if not w or not h:
            continue
        full = p.get("file_url") or ("https://safebooru.org/images/%s/%s" % (p.get("directory"), p.get("image")))
        prev = p.get("sample_url") or ("https://safebooru.org/samples/%s/sample_%s" % (p.get("directory"), p.get("image")))
        out.append(dict(site="sb", id=str(p.get("id")), score=int(p.get("score") or 0), w=w, h=h,
                        url=full, prev=prev, tags=(p.get("tags") or ""), rating=p.get("rating")))
    return out


def wh_fetch(q, page=1):
    r = get("https://wallhaven.cc/api/v1/search",
            {"q": q, "purity": "100", "categories": "010", "sorting": "relevance",
             "order": "desc", "page": page, "atleast": "1000x1400"})
    if not r:
        return []
    try:
        js = r.json()
    except Exception:
        return []
    out = []
    for p in js.get("data", []):
        try:
            w, h = int(p["dimension_x"]), int(p["dimension_y"])
        except Exception:
            continue
        if h <= w:
            continue
        out.append(dict(site="wh", id=str(p.get("id")), score=int(p.get("favorites") or 0), w=w, h=h,
                        url=p.get("path"), prev=(p.get("thumbs") or {}).get("large") or p.get("path"),
                        tags=" ".join([p.get("category") or ""] + (p.get("tags") or [])).strip(),
                        rating="s"))
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
        for pid in (0, 1, 2):
            got = sb_fetch(t, pid)
            print("  %s sb %s p%d -> %d" % (name, t, pid, len(got)), flush=True)
            pool += got
            if len(got) < 100:
                break
        if len(pool) >= 240:
            break
    for q in [name] + tags:
        for page in (1, 2, 3):
            got = wh_fetch(q, page)
            print("  %s wh %s p%d -> %d" % (name, q, page, len(got)), flush=True)
            pool += got
            if len(got) < 24:
                break
        if len(pool) >= 240:
            break
    print("== %s pool=%d" % (name, len(pool)), flush=True)

    seen, kept = set(), []
    pool.sort(key=lambda p: -(p["score"] or 0))
    for p in pool:
        key = p["site"] + ":" + str(p["id"])
        if key in seen or key in used:
            continue
        seen.add(key)
        w, h = p["w"], p["h"]
        if not p.get("url") or not p.get("prev"):
            continue
        r = h / w
        if r >= 1.2:
            if h < 1300 or w < 700:
                continue
        elif r >= 0.85:
            if h < 1700:
                continue
        else:
            if h < 1700 or w < 2000:
                continue
        if set(p["tags"].replace("(", " ").replace(")", " ").split()) & BAD:
            continue
        kept.append(p)
    print("   valid=%d" % len(kept), flush=True)

    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    n = 0
    for p in kept:
        if n >= PER_SERIES:
            break
        try:
            r = S.get(p["prev"], timeout=60)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            if im.size[0] < 300:
                continue
            w, h = im.size
            tw, th = 360, 640
            t = 16 / 9
            if h / w > 2.2:
                bg = ImageOps.fit(im, (tw, th), Image.LANCZOS).filter(ImageFilter.GaussianBlur(22))
                fg = im.copy()
                fg.thumbnail((tw, th), Image.LANCZOS)
                bg.paste(fg, ((tw - fg.width) // 2, (th - fg.height) // 2))
                prev_im = bg
            elif h / w > t:
                nh = int(w * t)
                y = int((h - nh) * 0.04)
                prev_im = im.crop((0, y, w, y + nh))
            else:
                nw = int(h * t)
                x = (w - nw) // 2
                prev_im = im.crop((x, 0, x + nw, h))
            fn = "%s_%02d.jpg" % (slug, n)
            prev_im.save(os.path.join(PREV, fn), "JPEG", quality=84, optimize=True)
            cands.append(dict(series=name, slug=slug, idx=n, file=fn, pid=p["id"], site=p["site"],
                              score=p["score"], w=p["w"], h=p["h"], url=p["url"], tags=p["tags"][:400]))
            n += 1
        except Exception as e:
            print("   dl err", p.get("site"), p.get("id"), type(e).__name__, flush=True)
        time.sleep(0.3)
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
