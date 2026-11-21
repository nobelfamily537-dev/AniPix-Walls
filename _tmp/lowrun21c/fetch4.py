#!/usr/bin/env python3
"""Low-count run 2026-11-21, lean fetch: one group of series per job, commit after each series."""
import hashlib, io, json, os, re, subprocess, time
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json,text/plain,*/*",
      "Referer": "https://konachan.net/"}

GROUPS = {
    "A": [
        ("a silent voice",    ["koe_no_katachi", "nishimiya_shouko", "ishida_shouya", "a_silent_voice"]),
        ("akatsuki no yona",  ["akatsuki_no_yona", "yona_(akatsuki_no_yona)", "son_hak", "yona"]),
        ("food wars",         ["shokugeki_no_souma", "tadokoro_megumi", "yukihira_souma", "nakiri_erina"]),
        ("chihayafuru",       ["chihayafuru", "ayase_chihaya", "mashima_taichi"]),
        ("the cat returns",   ["neko_no_onggaeshi", "baron_humbert_von_gikkingen", "haru_(neko_no_onggaeshi)"]),
    ],
    "B": [
        ("ponyo",             ["gake_no_ue_no_ponyo", "ponyo_(gake_no_ue_no_ponyo)", "sosuke_(ponyo)"]),
        ("porco rosso",       ["kurenai_no_buta", "porco_rosso", "fio_piccolo"]),
        ("the wind rises",    ["kaze_tachinu", "horikoshi_jirou", "satomi_naoko"]),
        ("oregairu",          ["yahari_ore_no_seishun_love_comedy_wa_machigatteiru", "yukinoshita_yukino", "yuigahama_yui", "hiki_gaya_hachiman"]),
        ("bubble",            ["bubble_(film)", "utai_(bubble)", "hibiki_(bubble)"]),
    ],
    "C": [
        ("kill la kill",      ["kill_la_kill", "matoi_ryuuko", "kiryuin_satsuki", "mankanshoku_mako"]),
        ("vinland saga",      ["vinland_saga", "thorfinn_(vinland_saga)", "askeladd", "canute_(vinland_saga)"]),
        ("seven deadly sins", ["nanatsu_no_taizai", "elizabeth_liones", "meliodas", "escanor"]),
        ("rurouni kenshin",   ["rurouni_kenshin", "himura_kenshin", "kamiya_kaoru", "shishio_makoto"]),
        ("noragami",          ["noragami", "yato_(noragami)", "ikishima_hiori", "yukine"]),
        ("fire force",        ["enen_no_shouboutai", "tamaki_kotatsu", "kusakabe_shinra", "arthur_boyle"]),
    ],
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
       "vector", "lineart", "line_art", "blood", "gore", "guro", "game_cg", "cgi",
       "anime_screencap", "screen_capture", "redraw", "official_art", "promotional_art",
       "key_visual", "poster", "banner", "album", "cover", "movie_poster", "bad_pixiv_id",
       "commentary", "commentary_request", "translation_request", "character_request", "artist_request",
       "wide_image", "phone_wallpaper", "variant_set", "resolution_mismatch", "partially_translated",
       "chinese_text", "korean_text", "japanese_text", "loli", "child",
       "aged_down", "muscular", "abs", "sweat", "tongue", "pov", "faceless_male", "male_focus",
       "greeting_card", "calendar", "sticker", "meme", "logo_parody", "fake_screenshot",
       "crying", "tears", "snot", "injury", "wound", "smoking", "cigarette", "alcohol", "drunk",
       "gun", "weapon", "blood_on_face", "scared", "angry", "screaming", "torn_clothes"}

OUT = "_tmp/lowrun21c"
PREV = os.path.join(OUT, "prev")
SHEETS = os.path.join(OUT, "sheets")
os.makedirs(PREV, exist_ok=True)
os.makedirs(SHEETS, exist_ok=True)

PER_SERIES = 18
GROUP = os.environ.get("GROUP", "A")
SERIES = GROUPS[GROUP]


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


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


def get(url, params, timeout=15, tries=2):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout)
            if r.status_code == 200:
                return r
            print("  HTTP", r.status_code, flush=True)
        except Exception as e:
            print("  ERR", type(e).__name__, flush=True)
        time.sleep(1.5)
    return None


def fetch_site(base, tag, pages=(1, 2)):
    out = []
    for page in pages:
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


data = json.load(open("wallpapers.json", encoding="utf-8"))
existing_ids, existing_urls = set(), set()
for cat, items in data["categories"].items():
    for e in items:
        existing_ids.add(e["id"])
        for k in ("full", "thumb", "alt"):
            if e.get(k):
                existing_urls.add(e[k])


def wid_for(url):
    return "wpx" + hashlib.sha1(url.encode()).hexdigest()[:10]


def commit(msg):
    subprocess.run(["git", "add", "-A", OUT], check=False)
    if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode == 0:
        print("nothing to commit", flush=True)
        return
    subprocess.run(["git", "-c", "user.name=AniPix Bot", "-c", "user.email=nobelfamily537@gmail.com",
                    "commit", "-q", "-m", msg], check=False)
    for _ in range(4):
        r = subprocess.run(["git", "push", "-q"], capture_output=True, text=True)
        if r.returncode == 0:
            print("PUSHED", msg, flush=True)
            return
        print("push failed, rebasing", r.stderr[-200:], flush=True)
        subprocess.run(["git", "pull", "--rebase", "-q", "--no-edit"], capture_output=True, text=True)
        time.sleep(2)


cands_path = os.path.join(OUT, "cands_%s.json" % GROUP)
cands = json.load(open(cands_path)) if os.path.exists(cands_path) else []
done = {c["series"] for c in cands}
print("group", GROUP, "already done:", sorted(done), flush=True)

for key, tags in SERIES:
    if key in done:
        continue
    pool = []
    for t in tags:
        got = fetch_site("https://konachan.net/post.json", t)
        print("  %s tag %s -> %d" % (key, t, len(got)), flush=True)
        pool += got
    if len(pool) < 25:
        for t in tags:
            got = fetch_site("https://yande.re/post.json", t)
            print("  %s YANDE %s -> %d" % (key, t, len(got)), flush=True)
            pool += got
    print("== %s pool=%d" % (key, len(pool)), flush=True)

    seen, kept = set(), []
    pool.sort(key=lambda p: -(p["score"] or 0))
    for p in pool:
        u = p.get("url")
        if not u or str(p["id"]) in seen:
            continue
        seen.add(str(p["id"]))
        if u in existing_urls or wid_for(u) in existing_ids:
            continue
        w, h = p["w"], p["h"]
        if not w or not h or not p.get("prev"):
            continue
        r = h / w
        if r >= 1.2:                      # portrait
            if h < 1150 or w < 620:
                continue
        elif r >= 0.85:                   # squarish
            if h < 1500:
                continue
        else:                             # landscape -> centre-crop to 9:16
            if h < 1080 or w < 1920:
                continue
        if set(p["tags"].split()) & BAD:
            continue
        if p.get("rating") not in ("s", None):
            continue
        kept.append(p)
    print("   valid=%d" % len(kept), flush=True)

    slug = slugify(key)
    n = 0
    for p in kept:
        if n >= PER_SERIES:
            break
        try:
            r = requests.get(p["prev"], headers=UA, timeout=15)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            fn = "%s_%02d.jpg" % (slug, n)
            render(im).save(os.path.join(PREV, fn), "JPEG", quality=84, optimize=True)
            cands.append(dict(series=key, slug=slug, idx=n, file=fn, pid=p["id"], site=p["site"],
                              score=p["score"], w=p["w"], h=p["h"], url=p["url"], tags=p["tags"]))
            n += 1
        except Exception as e:
            print("   dl err", p.get("id"), type(e).__name__, flush=True)
    print("   previews=%d" % n, flush=True)

    # contact sheet for this series
    items = [c for c in cands if c["slug"] == slug]
    if items:
        COLS, ROWS, CW, CH = 5, 3, 300, 533
        rows = (len(items) + COLS - 1) // COLS
        sheet = Image.new("RGB", (COLS * CW, rows * CH), (18, 18, 18))
        dr = ImageDraw.Draw(sheet)
        for k, c in enumerate(items):
            im = Image.open(os.path.join(PREV, c["file"])).convert("RGB").resize((CW, CH), Image.LANCZOS)
            x, y = (k % COLS) * CW, (k // COLS) * CH
            sheet.paste(im, (x, y))
            dr.rectangle([x, y, x + 34, y + 20], fill=(0, 0, 0))
            dr.text((x + 5, y + 5), str(c["idx"]), fill=(255, 255, 0))
        sheet.save(os.path.join(SHEETS, "%s.jpg" % slug), "JPEG", quality=86, optimize=True)

    json.dump(cands, open(cands_path, "w"), indent=1)
    commit("tmp: lowrun21 fetch %s (%s)" % (GROUP, slug))

print("GROUP %s DONE, total cands %d" % (GROUP, len(cands)), flush=True)
