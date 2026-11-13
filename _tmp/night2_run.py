#!/usr/bin/env python3
"""AniPix night gap-fill runner (fetch previews / publish approved picks)."""
import os, io, json, time, re, html, hashlib
import requests, numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
MODE = open("_tmp/night2_mode.txt").read().strip() if os.path.exists("_tmp/night2_mode.txt") else "fetch"
DATE = "2026-11-13"
BASE = "https://raw.githubusercontent.com/nobelfamily537-dev/AniPix-Walls/main"
TARGET = 9 / 16

SERIES = [
    ("mashle", "mashle", ["mashle", "mash_burnedead"]),
    ("ranma", "ranma 1/2", ["ranma_1/2", "saotome_ranma"]),
    ("drstone", "dr stone", ["dr._stone", "ishigami_senkuu"]),
    ("fireforce", "fire force", ["enen_no_shouboutai", "shinra_kusakabe"]),
    ("abyss", "made in abyss", ["made_in_abyss", "reg_(made_in_abyss)"]),
]

BAD = {"text","english_text","watermark","signature","artist_name","speech_bubble","comic","4koma",
       "multiple_views","character_sheet","translated","logo","border","frame","letterboxed",
       "twitter_username","web_address","dated","artist_logo","english_commentary","bad_id",
       "bad_pixiv_id","bad_twitter_id","official_art","sketch","monochrome","greyscale",
       "partially_colored","gun","vehicle","blood","gore","censored","manga","scan","sample",
       "no_humans","food","chibi","comic_panel","bikini","swimsuit","underwear","lingerie","panties",
       "bra","cleavage","no_bra","see_through","cameltoe","spread_legs","large_breasts","huge_breasts",
       "ass","nude","naked","topless","wet","bed","bottomless","sideboob","underboob","loli",
       "cropped","faceless","pantyshot","upskirt","skirt_lift","screencap","anime_screencap",
       "multiple_boys","multiple_girls","huge_filesize","absurdres","highres","wide_image"}


def get(url, params=None, tries=3, sleep=1.0):
    for _ in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=60)
            if r.status_code == 200:
                time.sleep(sleep)
                return r
            print("  HTTP", r.status_code, url, flush=True)
        except Exception as e:
            print("  ERR", e, flush=True)
        time.sleep(3)
    return None


def wallhaven(q):
    out = []
    for ratios, atleast in (("portrait", "1200x1600"), ("landscape", "2560x1440")):
        for page in (1, 2):
            r = get("https://wallhaven.cc/api/v1/search",
                    {"q": q, "categories": "010", "purity": "100", "ratios": ratios,
                     "atleast": atleast, "sorting": "favorites", "page": page})
            if not r:
                break
            try:
                js = r.json()
            except Exception:
                break
            for d in js.get("data", []):
                out.append(dict(src="wh", cid=d["id"], score=(d.get("favorites") or 0),
                                w=d["dimension_x"], h=d["dimension_y"], url=d["path"],
                                prev=(d.get("thumbs") or {}).get("large") or d["path"],
                                tags=" ".join(t["name"] for t in d.get("tags", []))))
            if js.get("meta", {}).get("current_page", 1) >= js.get("meta", {}).get("last_page", 1):
                break
    return out


def safebooru(tag):
    out = []
    for pid in (0, 1):
        r = get("https://safebooru.org/index.php",
                {"page": "dapi", "s": "post", "q": "index", "tags": tag + " sort:score:desc",
                 "limit": 100, "pid": pid}, sleep=1.2)
        if not r:
            break
        for m in re.finditer(r"<post\b([^>]*)/?>", r.text):
            a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
            try:
                w, h, sc = int(a.get("width", 0)), int(a.get("height", 0)), int(a.get("score", 0))
            except Exception:
                continue
            if sc < 30 or w < 900:
                continue
            prev = a.get("sample_url") or ""
            if "sample" not in prev:
                prev = f"https://safebooru.org/images/{a.get('directory')}/{a.get('image')}"
            out.append(dict(src="sb", cid="sb" + a.get("id", ""), score=sc, w=w, h=h,
                            url=f"https://safebooru.org/images/{a.get('directory')}/{a.get('image')}",
                            prev=prev, tags=html.unescape(a.get("tags", ""))))
    return out


def plausible(p):
    w, h = p["w"], p["h"]
    if not w or not h:
        return False
    r = h / w
    return 0.5 <= r <= 2.2 and h >= 900


def smart_crop(im):
    w, h = im.size
    r = h / w
    if r > TARGET * 1.02:
        nh = int(w / TARGET)
        y = int((h - nh) * 0.05)
        return im.crop((0, y, w, y + nh))
    if r >= TARGET:
        return im
    nw = int(h * TARGET)
    gw = 200
    g = im.convert("L").resize((gw, max(20, int(gw * h / w))), Image.LANCZOS)
    a = np.asarray(g.filter(ImageFilter.FIND_EDGES), dtype=np.float32)
    col = np.convolve(a.mean(axis=0), np.ones(7) / 7, "same")
    win = max(2, int(round(nw * gw / w)))
    xs = np.arange(len(col) - win + 1)
    if len(xs) <= 0:
        x = (w - nw) // 2
    else:
        centre = (len(col) - win) / 2
        bias = np.exp(-((xs - centre) ** 2) / (2 * (len(col) * 0.30) ** 2))
        scores = np.array([col[x:x + win].sum() for x in xs]) * bias
        x = int(xs[int(np.argmax(scores))] * w / gw)
    x = max(0, min(w - nw, x))
    return im.crop((x, 0, x + nw, h))


def flatten(im):
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        flat = Image.new("RGB", im.size, (255, 255, 255))
        flat.paste(im, mask=im.split()[-1])
        return flat
    return im.convert("RGB")


def do_fetch():
    OUT = "_tmp/n2/prev"
    SHEETS = "_tmp/n2/sheets"
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(SHEETS, exist_ok=True)
    used = set()
    wp = json.load(open("wallpapers.json"))
    for _cat, ents in wp["categories"].items():
        for e in ents:
            for f in (e.get("full"), e.get("thumb")):
                m = re.search(r"wallhaven-([a-z0-9]+)\.(?:jpg|png|jpeg|webp)", f or "")
                if m:
                    used.add(m.group(1))
    allc = []
    for slug, name, sbtags in SERIES:
        pool = wallhaven(slug.replace("-", " "))
        for t in sbtags:
            pool += safebooru(t)
        seen, kept = set(), []
        pool.sort(key=lambda p: -(p["score"] or 0))
        for p in pool:
            if p["cid"] in seen:
                continue
            seen.add(p["cid"])
            if p["src"] == "wh" and p["cid"] in used:
                continue
            if not plausible(p):
                continue
            if set(p["tags"].split()) & BAD:
                continue
            kept.append(p)
        kept = kept[:12]
        print(f"== {slug}: pool={len(pool)} kept={len(kept)}", flush=True)
        mine = []
        for i, p in enumerate(kept):
            fn = f"{slug}_{i:02d}.jpg"
            try:
                r = requests.get(p["prev"], headers=UA, timeout=60)
                r.raise_for_status()
                im = flatten(Image.open(io.BytesIO(r.content)))
                if im.width < 380:
                    raise ValueError("tiny")
                ImageOps.fit(smart_crop(im), (450, 800), method=Image.LANCZOS).save(
                    os.path.join(OUT, fn), "JPEG", quality=82, optimize=True)
                rec = dict(slug=slug, name=name, idx=len(allc), file=fn, **p)
                allc.append(rec)
                mine.append(rec)
            except Exception as e:
                print("  err", fn, e, flush=True)
            time.sleep(0.2)
        cw, ch, cols = 380, 676, 3
        for s in range(0, len(mine), 6):
            chunk = mine[s:s + 6]
            rows = (len(chunk) + cols - 1) // cols
            sheet = Image.new("RGB", (cw * cols, ch * rows), (15, 15, 15))
            d = ImageDraw.Draw(sheet)
            for i, rec in enumerate(chunk):
                im = Image.open(os.path.join(OUT, rec["file"])).resize((cw, ch), Image.LANCZOS)
                x, y = (i % cols) * cw, (i // cols) * ch
                sheet.paste(im, (x, y))
                d.rectangle([x, y, x + 52, y + 26], fill=(0, 0, 0))
                d.text((x + 6, y + 7), str(rec["idx"]), fill=(255, 255, 0))
            sheet.save(os.path.join(SHEETS, f"{slug}_{s // 6}.jpg"), "JPEG", quality=85, optimize=True)
    json.dump(allc, open("_tmp/n2/cands.json", "w"), indent=1)
    print("TOTAL", len(allc), flush=True)


def do_publish():
    cands = json.load(open("_tmp/n2/cands.json"))
    picks = json.load(open("_tmp/night2_picks.json"))
    by_idx = {c["idx"]: c for c in cands}
    wp = json.load(open("wallpapers.json"))
    have = {e["id"] for c in wp["categories"].values() for e in c}
    have_urls = {e.get("full") for c in wp["categories"].values() for e in c}
    FIN = "_tmp/n2/final"
    os.makedirs(FIN, exist_ok=True)
    added = []
    for pk in picks:
        c = by_idx.get(pk["idx"])
        if not c:
            print("no cand", pk["idx"], flush=True)
            continue
        iid = "wpx" + hashlib.md5((c["slug"] + "|" + c["cid"]).encode()).hexdigest()[:10]
        cat = pk["cat"]
        full_url = f"{BASE}/{cat}/{iid}.jpg"
        if iid in have or full_url in have_urls:
            print("dup", iid, flush=True)
            continue
        ok = False
        for _ in range(3):
            try:
                r = requests.get(c["url"], headers=UA, timeout=180)
                r.raise_for_status()
                im = flatten(Image.open(io.BytesIO(r.content)))
                full = ImageOps.fit(smart_crop(im), (1080, 1920), method=Image.LANCZOS)
                full.save(os.path.join(FIN, iid + ".jpg"), "JPEG", quality=95, optimize=True)
                full.resize((360, 640), Image.LANCZOS).save(
                    os.path.join(FIN, iid + "_thumb.jpg"), "JPEG", quality=80, optimize=True)
                ok = True
                break
            except Exception as e:
                print("dl err", iid, e, flush=True)
                time.sleep(5)
        if not ok:
            continue
        os.makedirs(cat, exist_ok=True)
        open(os.path.join(cat, iid + ".jpg"), "wb").write(open(os.path.join(FIN, iid + ".jpg"), "rb").read())
        open(os.path.join(cat, iid + "_thumb.jpg"), "wb").write(open(os.path.join(FIN, iid + "_thumb.jpg"), "rb").read())
        wp["categories"][cat].insert(0, {
            "id": iid,
            "thumb": f"{BASE}/{cat}/{iid}_thumb.jpg",
            "full": full_url,
            "alt": full_url,
            "tags": pk["tags"],
            "date": DATE,
        })
        have.add(iid)
        have_urls.add(full_url)
        added.append((cat, iid, c["slug"], c["src"], c["cid"]))
        print("added", cat, iid, c["slug"], flush=True)
    wp["version"] = int(wp.get("version", 0)) + 1
    wp["last_updated"] = DATE
    with open("wallpapers.json", "w", encoding="utf-8") as f:
        json.dump(wp, f, ensure_ascii=False, separators=(",", ":"))
    json.dump(added, open("_tmp/n2/added.json", "w"), indent=1)
    print("PUBLISHED", len(added), "version", wp["version"], flush=True)


if MODE == "publish":
    do_publish()
else:
    do_fetch()
