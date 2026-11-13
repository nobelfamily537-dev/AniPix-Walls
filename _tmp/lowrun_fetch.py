#!/usr/bin/env python3
"""Low-count run v5: wallhaven with per-image tag verification + konachan fallback."""
import os, io, json, time, re
import requests
from PIL import Image, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

# (display, AniPix tag, alt, category, wallhaven queries, required wallhaven tag substrings, booru tags)
SERIES = [
    ("soul eater", "soul eater", "soul eater", "anime",
     ["soul eater", "maka albarn", "soul evans"], ["soul eater"], ["soul_eater"]),
    ("princess mononoke", "princess mononoke", "mononoke hime", "anime",
     ["mononoke hime", "princess mononoke", "san mononoke"], ["mononoke"], ["mononoke_hime"]),
    ("dungeon meshi", "dungeon meshi", "delicious in dungeon", "anime",
     ["dungeon meshi", "marcille donato", "delicious in dungeon"], ["dungeon meshi", "delicious in dungeon"], ["dungeon_meshi"]),
    ("zenless zone zero", "zenless zone zero", "zzz", "game",
     ["zenless zone zero", "ellen joe", "hoshimi miyabi"], ["zenless zone zero"], ["zenless_zone_zero"]),
    ("blue lock", "blue lock", "blue lock", "anime",
     ["blue lock", "isagi yoichi", "bachira meguru"], ["blue lock"], ["blue_lock"]),
    ("spice and wolf", "ookami to koushinryou", "spice and wolf", "anime",
     ["spice and wolf", "holo spice and wolf", "ookami to koushinryou"], ["spice and wolf", "ookami to koushinryou"], ["ookami_to_koushinryou"]),
    ("sailor moon", "sailor moon", "bishoujo senshi sailor moon", "anime",
     ["sailor moon", "sailor moon crystal"], ["sailor moon"], ["sailor_moon"]),
    ("black clover", "black clover", "black clover", "anime",
     ["black clover", "asta black clover", "noelle silva"], ["black clover"], ["black_clover"]),
    ("one punch man", "one punch man", "one-punch man", "anime",
     ["one punch man", "saitama", "genos"], ["one punch man", "one-punch man"], ["one-punch_man"]),
    ("violet evergarden", "violet evergarden", "violet evergarden", "anime",
     ["violet evergarden"], ["violet evergarden"], ["violet_evergarden"]),
    ("kaiju no. 8", "kaiju no. 8", "kaijuu 8-gou", "anime",
     ["kaiju no 8", "kaiju no. 8", "kafka hibino"], ["kaiju no. 8", "kaiju no 8", "kaijuu"], ["kaijuu_8-gou"]),
    ("haikyuu", "haikyuu", "haikyuu!!", "anime",
     ["haikyuu", "hinata shouyou"], ["haikyuu"], ["haikyuu!!"]),
    ("dan da dan", "dan da dan", "dandadan", "anime",
     ["dan da dan", "dandadan", "momo ayase"], ["dan da dan", "dandadan"], ["dandadan"]),
    ("fullmetal alchemist", "fullmetal alchemist", "fma", "anime",
     ["fullmetal alchemist", "edward elric"], ["fullmetal alchemist"], ["fullmetal_alchemist"]),
]
BACKUP = {"kaiju no. 8", "haikyuu", "dan da dan", "fullmetal alchemist"}

BAD = {"text", "english_text", "watermark", "signature", "artist_name", "speech_bubble",
       "comic", "4koma", "multiple_views", "character_sheet", "translated", "logo",
       "twitter_username", "web_address", "dated", "artist_logo", "english_commentary",
       "bad_id", "sketch", "monochrome", "greyscale", "partially_colored", "gun", "mecha",
       "vehicle", "blood", "gore", "censored", "manga", "scan", "sample", "chibi",
       "comic_panel", "bikini", "swimsuit", "underwear", "lingerie", "panties", "bra",
       "cleavage", "no_bra", "see_through", "spread_legs", "large_breasts", "huge_breasts",
       "ass", "nude", "naked", "topless", "wet", "bed", "bottomless", "sideboob", "underboob",
       "photo", "photograph", "cosplay", "screencap", "screenshot", "reference_sheet",
       "concept_art", "lowres", "map", "real_world_location", "crossover", "3d",
       "cosplay_costume", "quote", "lyrics", "banner", "border", "framed"}

OUT = "_tmp/lowrun/prev"
os.makedirs(OUT, exist_ok=True)
PRIOR = set()
if os.path.exists("_tmp/prior_ids.txt"):
    PRIOR = {l.strip() for l in open("_tmp/prior_ids.txt") if l.strip()}


def render(im, size=(360, 640)):
    tw, th = size
    t = tw / th
    w, h = im.size
    r = w / h  # width / height
    if r > t:                      # wider than 9:16 -> crop sides
        nw = int(h * t)
        x = (w - nw) // 2
        im = im.crop((x, 0, x + nw, h))
    else:                          # taller -> crop top/bottom (bias to upper part)
        nh = int(w / t)
        y = int((h - nh) * (0.08 if h / w < 2.05 else 0.0))
        im = im.crop((0, y, w, y + nh))
    return im.resize((tw, th), Image.LANCZOS)


def get(url, params=None, timeout=30):
    for _ in range(2):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout)
            if r.status_code == 200:
                time.sleep(1.05)
                return r
            print("  HTTP", r.status_code, url, flush=True)
        except Exception as e:
            print("  ERR", type(e).__name__, url, flush=True)
        time.sleep(2)
    return None


def wh_search(q):
    out = []
    for page in (1, 2):
        r = get("https://wallhaven.cc/api/v1/search",
                {"q": q, "categories": "010", "purity": "100", "atleast": "1080x1500",
                 "sorting": "favorites", "page": page})
        if not r:
            break
        try:
            js = r.json()
        except Exception:
            break
        for d in js.get("data", []):
            out.append(dict(src="wallhaven", pid="w" + d["id"], score=d.get("favorites") or 0,
                            w=d["dimension_x"], h=d["dimension_y"], url=d["path"]))
        if js.get("meta", {}).get("current_page", 1) >= js.get("meta", {}).get("last_page", 1):
            break
    return out


def wh_tags(pid):
    r = get("https://wallhaven.cc/api/v1/w/" + pid[1:])
    if not r:
        return None
    try:
        d = r.json()["data"]
        return [t["name"].lower() for t in d.get("tags", [])]
    except Exception:
        return None


def konachan(btags):
    out = []
    for page in (1, 2, 3):
        r = get("https://konachan.net/post.json",
                {"tags": btags + " rating:s", "limit": 100, "page": page})
        if not r:
            break
        try:
            js = r.json()
        except Exception:
            break
        if not js:
            break
        for d in js:
            out.append(dict(src="konachan", pid="k%d" % d["id"], score=d.get("score") or 0,
                            w=d["width"], h=d["height"], url=d["jpeg_url"],
                            prev=d.get("sample_url") or d["jpeg_url"],
                            tags=(d.get("tags") or "").split()))
    return out


def safebooru(btags):
    out = []
    for page in (0, 1, 2):
        r = get("https://safebooru.org/index.php",
                {"page": "dapi", "s": "post", "q": "index", "json": 1,
                 "tags": btags + " sort:score:desc", "limit": 100, "pid": page})
        if not r:
            break
        try:
            js = r.json()
        except Exception:
            break
        if not js:
            break
        for d in js:
            d = {k.lower(): v for k, v in d.items()}
            try:
                w, h = int(d["width"]), int(d["height"])
            except Exception:
                continue
            url = "https://safebooru.org/images/%s/%s" % (d["directory"], d["image"])
            out.append(dict(src="safebooru", pid="s%s" % d["id"], score=d.get("score") or 0,
                            w=w, h=h, url=url, prev=url, tags=(d.get("tags") or "").split()))
    return out


def aspect_ok(p):
    r = p["h"] / p["w"]
    if 1.3 <= r <= 2.3:
        return True
    if r <= 0.85 and p["w"] >= 2000:   # big landscape, centre-crop is fine
        return True
    return False


cands = []
for name, tag, alt, cat, wqs, req, btags in SERIES:
    lim = 10 if name in BACKUP else 20
    seen, picked = set(), []

    # ---- wallhaven with tag verification ----
    pool = []
    for q in wqs:
        pool += wh_search(q)
    pool = [p for p in pool if p["pid"] not in seen and p["pid"] not in PRIOR and aspect_ok(p)]
    pool.sort(key=lambda p: (0 if p["h"] / p["w"] >= 1.3 else 1, -(p["score"] or 0)))
    print("== %s wallhaven pool=%d" % (name, len(pool)), flush=True)
    checked = 0
    for p in pool:
        if len(picked) >= lim or checked >= 45:
            break
        checked += 1
        tg = wh_tags(p["pid"])
        if tg is None:
            continue
        if not any(any(req_s in t for t in tg) for req_s in req):
            continue
        if set(tg) & BAD:
            continue
        seen.add(p["pid"])
        p["tags"] = tg[:40]
        p["prev"] = p["url"]
        picked.append(p)
    print("   wh verified=%d (checked %d)" % (len(picked), checked), flush=True)

    # ---- booru fallback ----
    if len(picked) < lim:
        bpool = []
        for bt in btags:
            bpool += konachan(bt)
        if len(bpool) < 60:
            for bt in btags:
                bpool += safebooru(bt)
        bs = set(btags)
        extra = []
        for p in bpool:
            if p["pid"] in seen or p["pid"] in PRIOR or not aspect_ok(p):
                continue
            tg = set(p["tags"])
            if not (tg & bs) or (tg & BAD):
                continue
            seen.add(p["pid"])
            extra.append(p)
        extra.sort(key=lambda p: (0 if p["h"] / p["w"] >= 1.3 else 1, -(p["score"] or 0)))
        picked += extra[:lim - len(picked)]
        print("   +booru=%d" % len(extra), flush=True)

    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    n = 0
    for p in picked:
        try:
            r = requests.get(p.get("prev") or p["url"], headers=UA, timeout=60)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            if im.width < 400:
                continue
            fn = "%s_%02d.jpg" % (slug, n)
            render(im).save(os.path.join(OUT, fn), "JPEG", quality=84, optimize=True)
            cands.append(dict(series=name, tag=tag, alt=alt, cat=cat, file=fn, src=p["src"],
                              pid=p["pid"], score=p["score"], w=p["w"], h=p["h"],
                              url=p["url"], tags=p.get("tags", [])[:40]))
            n += 1
        except Exception as e:
            print("   dl err", p.get("pid"), type(e).__name__, flush=True)
        time.sleep(0.05)
    print("   previews=%d" % n, flush=True)

json.dump(cands, open("_tmp/lowrun/cand.json", "w"), indent=1)
print("TOTAL", len(cands), flush=True)
