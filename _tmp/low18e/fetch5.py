#!/usr/bin/env python3
"""Low-count run stage 1c: konachan candidates for the 10 chosen series."""
import io, json, os, re, time
from concurrent.futures import ThreadPoolExecutor
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Referer": "https://konachan.net/"}

SERIES = [
    ("my dress up darling", ["kitagawa_marin", "sono_bisque_doll_wa_koi_wo_suru", "gojou_wakana"], "sono bisque doll wa koi wo suru", ["kitagawa_marin"]),
    ("bunny girl senpai", ["sakurajima_mai", "seishun_buta_yarou"], "rascal does not dream of bunny girl senpai", ["sakurajima_mai"]),
    ("darling in the franxx", ["zero_two_(darling_in_the_franxx)", "darling_in_the_franxx", "ichigo_(darling_in_the_franxx)"], "darling in the franxx", ["zero_two_(darling_in_the_franxx)", "ichigo_(darling_in_the_franxx)"]),
    ("cyberpunk edgerunners", ["lucy_(cyberpunk)", "cyberpunk:_edgerunners", "rebecca_(cyberpunk)"], "cyberpunk edgerunners", ["lucy_(cyberpunk)", "rebecca_(cyberpunk)"]),
    ("konosuba", ["megumin", "aqua_(konosuba)", "darkness_(konosuba)", "kono_subarashii_sekai_ni_shukufuku_wo!"], "kono subarashii sekai ni shukufuku wo", ["megumin", "aqua_(konosuba)", "darkness_(konosuba)"]),
    ("laid back camp", ["shiraishi_rin", "oomachi_nadeshiko", "yuru_camp", "inuyama_aoi"], "yuru camp", ["shiraishi_rin", "oomachi_nadeshiko", "inuyama_aoi"]),
    ("steins gate", ["makise_kurisu", "steins;gate", "shiina_mayuri"], "steins gate", ["makise_kurisu", "shiina_mayuri"]),
    ("fullmetal alchemist", ["fullmetal_alchemist", "edward_elric", "winry_rockbell", "riza_hawkeye"], "fullmetal alchemist", ["edward_elric", "winry_rockbell", "riza_hawkeye"]),
    ("code geass", ["code_geass", "lamperouge_lelouch", "c.c.", "kouzuki_kallen"], "code geass", ["lamperouge_lelouch", "c.c.", "kouzuki_kallen"]),
    ("nisekoi", ["kirisaki_chitoge", "onodera_kosaki", "nisekoi"], "nisekoi", ["kirisaki_chitoge", "onodera_kosaki"]),
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
       "anime_screencap", "screen_capture", "redraw", "promotional_art",
       "key_visual", "poster", "banner", "album", "cover", "movie_poster", "bad_pixiv_id",
       "commentary", "commentary_request", "translation_request", "character_request", "artist_request",
       "wide_image", "variant_set", "resolution_mismatch", "partially_translated",
       "chinese_text", "korean_text", "japanese_text", "loli", "child",
       "aged_down", "muscular", "abs", "sweat", "tongue", "pov", "faceless_male", "male_focus",
       "greeting_card", "calendar", "sticker", "meme", "logo_parody", "fake_screenshot",
       "seiyuu", "voice_actor", "magazine", "book", "dakimakura", "pillow", "figure", "toy", "3d",
       "real_life", "photo_(medium)", "cartoon", "western", "comic_book", "greyscale_image",
       "bikini_armor", "bondage", "restrained", "gag", "futanari", "yaoi", "yuri", "kiss", "nipples",
       "areolae", "pubic_hair", "pussy", "penis", "sex", "cum", "hugging", "tail", "animal_ears",
       "cosplay_photo", "duplicate", "cropped", "huge_filesize", "absurdres_placeholder"}

OUT = "_tmp/low18e"
PREV = os.path.join(OUT, "prev")
SHEETS = os.path.join(OUT, "sheets")
os.makedirs(PREV, exist_ok=True)
os.makedirs(SHEETS, exist_ok=True)
PER = 20


def render(im, size=(360, 640)):
    w, h = im.size
    r = h / w
    tw, th = size
    t = 16 / 9
    if r > 2.3:
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


def fetch_posts(tag):
    out = []
    for page in (1, 2, 3):
        js = None
        for attempt in range(3):
            try:
                r = requests.get("https://konachan.net/post.json",
                                 params={"tags": tag + " rating:s", "limit": 100, "page": page},
                                 headers=UA, timeout=25)
                if r.status_code == 200:
                    js = r.json()
                    break
                print("  HTTP", r.status_code, tag, page, flush=True)
            except Exception as e:
                print("  ERR", type(e).__name__, tag, page, flush=True)
            time.sleep(3)
        if not js:
            break
        for p in js:
            out.append(dict(id=p.get("id"), score=p.get("score") or 0, w=p.get("width") or 0,
                            h=p.get("height") or 0, url=p.get("file_url"),
                            prev=p.get("sample_url") or p.get("jpeg_url") or p.get("file_url"),
                            tags=p.get("tags") or "", rating=p.get("rating")))
        if len(js) < 100:
            break
        time.sleep(0.6)
    return out


def dl(job):
    p, path = job
    err = ""
    for _ in range(2):
        try:
            r = requests.get(p["prev"], headers=UA, timeout=30)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            render(im).save(path, "JPEG", quality=84, optimize=True)
            return True
        except Exception as e:
            err = type(e).__name__
            time.sleep(2)
    print("   dl err", p.get("id"), err, flush=True)
    return False


used = set()
for f in ("_tmp/low18/used_pids.json", "_tmp/low18c/used_pids.json", "_tmp/low18d/used_pids.json", "_tmp/low18e/used_pids.json"):
    if os.path.exists(f):
        try:
            used |= set(str(x) for x in json.load(open(f)))
        except Exception:
            pass

cands = []
for name, tag, alias, chars in SERIES:
    pool = []
    for t in tag:
        pool += fetch_posts(t)
        if len(pool) >= 220:
            break
    print("== %s (%s): pool=%d" % (name, ",".join(tag), len(pool)), flush=True)
    seen, kept = set(), []
    pool.sort(key=lambda p: -(p["score"] or 0))
    for p in pool:
        if p["id"] in seen or str(p["id"]) in used:
            continue
        seen.add(p["id"])
        w, h = p["w"], p["h"]
        if not w or not h or not p.get("url") or not p.get("prev"):
            continue
        r = h / w
        if r >= 1.15:
            if h < 1100 or w < 600:
                continue
        elif r >= 0.9:
            if h < 1300:
                continue
        else:
            if w < 1600 or h < 900:
                continue
        if set(p["tags"].split()) & BAD:
            continue
        if p.get("rating") != "s":
            continue
        kept.append(p)
    print("   valid=%d" % len(kept), flush=True)
    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    take = kept[:PER]
    jobs = [(p, os.path.join(PREV, "%s_%02d.jpg" % (slug, i))) for i, p in enumerate(take)]
    with ThreadPoolExecutor(max_workers=10) as ex:
        oks = list(ex.map(dl, jobs))
    n = 0
    for (p, path), ok in zip(jobs, oks):
        if not ok:
            continue
        cands.append(dict(series=name, slug=slug, alias=alias, chars=chars, idx=n,
                          file=os.path.basename(path), pid=p["id"], score=p["score"],
                          w=p["w"], h=p["h"], url=p["url"], tags=p["tags"]))
        n += 1
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
            dr.rectangle([x, y, x + 36, y + 22], fill=(0, 0, 0))
            dr.text((x + 6, y + 6), str(c["idx"]), fill=(255, 255, 0))
        sheet.save(os.path.join(SHEETS, "%s_%d.jpg" % (slug, si // per)), "JPEG", quality=87, optimize=True)

print("TOTAL candidates", len(cands), flush=True)
print("sheets:", sorted(os.listdir(SHEETS)), flush=True)
