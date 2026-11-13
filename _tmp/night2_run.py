#!/usr/bin/env python3
"""AniPix night gap-fill runner v2 (fetch previews / publish approved picks)."""
import os, io, json, time, re, html, hashlib
import requests, numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": "AniPixBot/1.0 (wallpaper curator)"}
MODE = open("_tmp/night2_mode.txt").read().strip() if os.path.exists("_tmp/night2_mode.txt") else "fetch"
DATE = "2026-11-13"
BASE = "https://raw.githubusercontent.com/nobelfamily537-dev/AniPix-Walls/main"
TARGET = 9 / 16

SERIES = [("fireforce", "fire force", ["tamaki_kotatsu", "maki_ohteru", "shinmon_benimaru", "iris_(enen_no_shouboutai)", "joker_(enen_no_shouboutai)", "arthur_boyle", "kusakabe_shinra"]), ("ranma", "ranma 1/2", ["tendou_kasumi", "tendou_nabiki", "kuonji_ukyou", "hibiki_ryouga"])] + [("fireforce", "fire force", ["tamaki_kotatsu", "maki_ohteru", "shinmon_benimaru", "iris_(enen_no_shouboutai)", "joker_(enen_no_shouboutai)", "arthur_boyle", "kusakabe_shinra"]), ("ranma", "ranma 1/2", ["tendou_kasumi", "tendou_nabiki", "kuonji_ukyou", "hibiki_ryouga"])] + [
    ("mashle", "mashle", ["mashle", "mash_burnedead", "dot_barrett", "lance_crown", "finn_ames"]),
    ("drstone", "dr stone", ["dr._stone", "ishigami_senkuu", "kohaku_(dr._stone)", "chrome_(dr._stone)"]),
    ("fireforce", "fire force", ["enen_no_shouboutai", "kusakabe_shinra", "tamaki_kotatsu", "arthur_boyle"]),
    ("ranma", "ranma 1/2", ["ranma_1/2", "saotome_ranma", "tendou_akane", "shampoo_(ranma_1/2)"]),
    ("abyss", "made in abyss", ["made_in_abyss", "reg_(made_in_abyss)", "nanachi", "riko_(made_in_abyss)", "ouzen"]),
]

BAD = {"text","english_text","watermark","signature","artist_name","speech_bubble","comic","4koma",
       "multiple_views","character_sheet","translated","logo","border","frame","letterboxed",
       "twitter_username","web_address","dated","artist_logo","english_commentary","bad_id",
       "bad_pixiv_id","bad_twitter_id","sketch","monochrome","greyscale","partially_colored",
       "gun","vehicle","blood","gore","censored","manga","scan","sample","no_humans","food","chibi",
       "comic_panel","bikini","swimsuit","underwear","lingerie","panties","bra","cleavage","no_bra",
       "see_through","cameltoe","spread_legs","large_breasts","huge_breasts","ass","nude","naked",
       "topless","wet","bed","bottomless","sideboob","underboob","loli","cropped","faceless",
       "pantyshot","upskirt","skirt_lift","screencap","anime_screencap","multiple_boys",
       "multiple_girls","huge_filesize","absurdres","wide_image","official_art","spoilers",
       "crossover","parody","real_world_location","photo_(medium)","3d","cosplay"}


def get(url, params=None, tries=3, sleep=1.0, as_json=False):
    for _ in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=60)
            if r.status_code == 200:
                time.sleep(sleep)
                return r.json() if as_json else r
            print("  HTTP", r.status_code, url, flush=True)
            if r.status_code in (403, 404):
                return None
        except Exception as e:
            print("  ERR", e, flush=True)
        time.sleep(3)
    return None


def danbooru(tag):
    out = []
    for page in (1, 2):
        js = get("https://danbooru.donmai.us/posts.json",
                 {"tags": tag + " rating:g order:score", "limit": 100, "page": page},
                 sleep=1.5, as_json=True)
        if not js:
            break
        for d in js:
            fu = d.get("file_url")
            if not fu:
                continue
            prev = d.get("large_file_url") or d.get("sample_url") or fu
            out.append(dict(src="db", cid="db" + str(d.get("id")),
                            score=d.get("score") or 0, w=d.get("image_width") or 0,
                            h=d.get("image_height") or 0, url=fu, prev=prev,
                            tags=(d.get("tag_string") or "")))
        if len(js) < 100:
            break
    return out


def wallhaven(q):
    out = []
    for ratios, atleast in (("portrait", "1200x1600"), ("landscape", "2560x1440")):
        js = get("https://wallhaven.cc/api/v1/search",
                 {"q": q, "categories": "010", "purity": "100", "ratios": ratios,
                  "atleast": atleast, "sorting": "favorites"}, sleep=1.0, as_json=True)
        if not js:
            continue
        for d in js.get("data", []):
            out.append(dict(src="wh", cid=d["id"], score=(d.get("favorites") or 0),
                            w=d["dimension_x"], h=d["dimension_y"], url=d["path"],
                            prev=(d.get("thumbs") or {}).get("large") or d["path"],
                            tags=" ".join(t["name"] for t in d.get("tags", []))))
    return out


def plausible(p):
    w, h = p["w"], p["h"]
    if not w or not h:
        return False
    r = h / w
    return 0.5 <= r <= 2.2 and h >= 1200 and w >= 700


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
    old = []
    if os.path.exists("_tmp/n2/cands.json"):
        try:
            old = json.load(open("_tmp/n2/cands.json"))
            old = [c for c in old if c.get("slug") in {s[0] for s in SERIES}]
        except Exception:
            old = []
    allc = list(old)
    seen = {c["cid"] for c in old}
    used = set()
    wp = json.load(open("wallpapers.json"))
    for _cat, ents in wp["categories"].items():
        for e in ents:
            for f in (e.get("full"), e.get("thumb")):
                m = re.search(r"wallhaven-([a-z0-9]+)\.(?:jpg|png|jpeg|webp)", f or "")
                if m:
                    used.add(m.group(1))

    for slug, name, tags_list in SERIES:
        pool = wallhaven(slug.replace("-", " "))
        for t in tags_list:
            pool += danbooru(t)
        seen_l, kept = set(), []
        pool.sort(key=lambda p: -(p["score"] or 0))
        for p in pool:
            if p["cid"] in seen_l or p["cid"] in seen:
                continue
            seen_l.add(p["cid"])
            if p["src"] == "wh" and p["cid"] in used:
                continue
            if not plausible(p):
                continue
            if set(p["tags"].split()) & BAD:
                continue
            kept.append(p)
        kept = kept[:14]
        print(f"== {slug}: pool={len(pool)} kept={len(kept)}", flush=True)
        mine = []
        for i, p in enumerate(kept):
            fn = f"{slug}_b{i:02d}.jpg"
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
                seen.add(rec["cid"])
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
                d.rectangle([x, y, x + 56, y + 26], fill=(0, 0, 0))
                d.text((x + 6, y + 7), str(rec["idx"]), fill=(255, 255, 0))
            sheet.save(os.path.join(SHEETS, f"{slug}_b{s // 6}.jpg"), "JPEG", quality=85, optimize=True)
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
