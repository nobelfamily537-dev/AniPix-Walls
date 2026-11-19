#!/usr/bin/env python3
"""Low-count run (17:00 IST, 2026-11-19) stage 1: fetch candidates + contact sheets."""
import io, json, os, re, time
import xml.etree.ElementTree as ET
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json,text/plain,*/*"}

OUT = "_tmp/low20"
PREV = os.path.join(OUT, "prev")
SHEETS = os.path.join(OUT, "sheets")
os.makedirs(PREV, exist_ok=True)
os.makedirs(SHEETS, exist_ok=True)

META = json.load(open(os.environ.get("META_FILE", os.path.join(OUT, "meta.json"))))["series"]
PER_SERIES = 24

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
       "chinese_text", "korean_text", "japanese_text", "loli", "child", "aged_down", "muscular", "abs",
       "sweat", "tongue", "pov", "faceless_male", "male_focus", "greeting_card", "calendar", "sticker",
       "meme", "logo_parody", "parody", "fake_screenshot", "3d", "ai-generated", "ai_assisted",
       "korean", "chinese", "sign", "english", "title", "subtitle", "emblem", "mosaic_censoring",
       "bar_censor", "torn_clothes", "blood_on_face", "scar", "injury", "nipples", "areolae",
       "pussy", "penis", "sex", "cum", "fellatio", "bondage", "gag", "collar_and_chain"}


def render(im, size=(180, 320)):
    w, h = im.size
    r = h / w
    t = 16 / 9
    if r > 2.2:
        bg = ImageOps.fit(im, size, method=Image.LANCZOS).filter(ImageFilter.GaussianBlur(22))
        fg = im.copy()
        fg.thumbnail(size, Image.LANCZOS)
        bg.paste(fg, ((size[0] - fg.width) // 2, (size[1] - fg.height) // 2))
        return bg
    if r > t:
        nh = int(w * t)
        y = int((h - nh) * 0.04)
        return im.crop((0, y, w, y + nh)).resize(size, Image.LANCZOS)
    nw = int(h / t)
    x = (w - nw) // 2
    return im.crop((x, 0, x + nw, h)).resize(size, Image.LANCZOS)


def get(url, params, timeout=45, referer=None):
    hdr = dict(UA)
    if referer:
        hdr["Referer"] = referer
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, headers=hdr, timeout=timeout)
            if r.status_code == 200:
                time.sleep(1.2)
                return r
            print("  HTTP", r.status_code, url, flush=True)
            time.sleep(5 + attempt * 5)
        except Exception as e:
            print("  ERR", type(e).__name__, str(e)[:60], flush=True)
            time.sleep(5)
    return None


def fetch_booru_json(base, tag):
    out = []
    for page in (1, 2):
        r = get(base, {"tags": tag + " rating:s", "limit": 100, "page": page}, referer="https://konachan.net/")
        if not r:
            break
        try:
            js = r.json()
        except Exception:
            break
        if not isinstance(js, list) or not js:
            break
        for p in js:
            out.append(dict(site=base.split("/")[2], id=p.get("id"), score=p.get("score") or 0,
                            w=p.get("width") or 0, h=p.get("height") or 0,
                            url=p.get("file_url"), prev=p.get("sample_url") or p.get("jpeg_url") or p.get("file_url"),
                            tags=p.get("tags") or "", md5=p.get("md5")))
        if len(js) < 100:
            break
    return out


def fetch_safebooru(tag):
    out = []
    for pid in (0, 1):
        r = get("https://safebooru.org/index.php",
                {"page": "dapi", "s": "post", "q": "index", "tags": tag, "limit": 100, "pid": pid},
                referer="https://safebooru.org/")
        if not r:
            break
        try:
            root = ET.fromstring(r.content)
        except Exception:
            break
        posts = root.findall("post")
        if not posts:
            break
        for p in posts:
            a = p.attrib
            try:
                w, h = int(a.get("width") or 0), int(a.get("height") or 0)
            except Exception:
                w = h = 0
            out.append(dict(site="safebooru.org", id=a.get("id"), score=int(a.get("score") or 0),
                            w=w, h=h, url=a.get("file_url"),
                            prev=a.get("sample_url") or a.get("preview_url") or a.get("file_url"),
                            tags=a.get("tags") or "", md5=a.get("md5")))
        if len(posts) < 100:
            break
    return out


used = set()
uf = os.path.join(OUT, "used_pids.json")
if os.path.exists(uf):
    used = set(str(x) for x in json.load(open(uf)))
print("already-used pids:", len(used), flush=True)

result = {}
for s in META:
    name = s["name"]
    pool, seen = [], set()
    for t in s["cats"]:
        batches = [("konachan.net", fetch_booru_json("https://konachan.net/post.json", t)),
                   ("konachan.com", fetch_booru_json("https://konachan.com/post.json", t)),
                   ("safebooru.org", fetch_safebooru(t))]
        for site, got in batches:
            print(" ", name, site, t, len(got), flush=True)
            for g in got:
                k = g.get("md5") or "%s:%s" % (g["site"], g["id"])
                if k in seen:
                    continue
                seen.add(k)
                pool.append(g)

    cands = []
    for p in pool:
        tg = set(p["tags"].split())
        if tg & BAD:
            continue
        if not p["url"] or not p["w"] or not p["h"]:
            continue
        r = p["h"] / p["w"]
        portrait = r >= 1.05 and p["w"] >= 900 and p["h"] >= 1200
        landscape = r >= 0.72 and p["w"] >= 1500 and p["h"] >= 1000
        if not (portrait or landscape):
            continue
        pid = "%s:%s" % (p["site"], p["id"])
        if pid in used:
            continue
        sc = (p["score"] or 0) * 3 + min(p["h"], 4000) / 60 + (60 if r > 1.5 else 0) - (0 if portrait else 45)
        cands.append(dict(p, pid=pid, sc=sc))

    cands.sort(key=lambda x: -x["sc"])
    cands = cands[:PER_SERIES]
    print("CANDIDATES", name, len(cands), flush=True)

    chosen, tiles = [], []
    for c in cands:
        try:
            rr = requests.get(c["prev"], headers=UA, timeout=45)
            rr.raise_for_status()
            im = Image.open(io.BytesIO(rr.content)).convert("RGB")
        except Exception as e:
            print("  prev fail", c["url"], type(e).__name__, flush=True)
            continue
        tiles.append((len(chosen), render(im)))
        c["idx"] = len(chosen)
        chosen.append(c)
        time.sleep(0.3)

    if not tiles:
        print("NO TILES", name, flush=True)
        result[name] = []
        continue

    cols = 6
    rows = (len(tiles) + cols - 1) // cols
    cw, ch = 180, 320
    sheet = Image.new("RGB", (cols * cw, max(rows, 1) * (ch + 22)), (18, 18, 22))
    dr = ImageDraw.Draw(sheet)
    for idx, t in tiles:
        cx = (idx % cols) * cw
        cy = (idx // cols) * (ch + 22)
        sheet.paste(t, (cx, cy))
        dr.rectangle([cx, cy + ch, cx + cw, cy + ch + 22], fill=(28, 28, 34))
        dr.text((cx + 4, cy + ch + 5), "#%02d %dx%d" % (idx, chosen[idx]["w"], chosen[idx]["h"]),
                fill=(240, 240, 240))
    sheet.save(os.path.join(SHEETS, re.sub(r"[^a-z0-9]+", "_", name.lower()) + ".jpg"),
               "JPEG", quality=86)
    for c in chosen:
        c.pop("prev", None)
    result[name] = chosen
    json.dump(chosen, open(os.path.join(OUT, "cand_%s.json" % re.sub(r"[^a-z0-9]+", "_", name.lower())), "w"), indent=1)
    time.sleep(1)

json.dump(result, open(os.path.join(OUT, "cands_all.json"), "w"), indent=1)
print("\nSUMMARY", json.dumps({k: len(v) for k, v in result.items()}), flush=True)
