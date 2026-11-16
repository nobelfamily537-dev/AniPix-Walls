import io, json, os, shutil, time
import requests
from PIL import Image, ImageDraw

OUT = os.path.dirname(os.path.abspath(__file__))
CAND = os.path.join(OUT, "cand")
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (AniPixBot)"})
WH = "https://wallhaven.cc/api/v1/search"

SHOWS = [
    ("monogatari", "monogatari", "Monogatari"),
    ("gundam", "gundam", "Gundam"),
    ("gintama", "gintama", "Gintama"),
    ("kuroko", "kuroko no basket", "Kuroko no Basket"),
    ("digimon", "digimon", "Digimon"),
    ("eightsix", "86 eighty six", "86 Eighty Six"),
    ("dorohedoro", "dorohedoro", "Dorohedoro"),
    ("champloo", "samurai champloo", "Samurai Champloo"),
    ("yurionice", "yuri on ice", "Yuri on Ice"),
]

BAD = set("""text english_text watermark signature logo comic multiple_views
character_sheet sketch monochrome greyscale lineart chibi cosplay photo realistic 3d
border letterboxed speech_bubble translated bad_anatomy lowres jpeg_artifacts
pixel_art collage scan screencap cropped partially_colored sensitive nsfw bikini swimsuit
underwear panties cleavage large_breasts huge_breasts spread_legs nipples ass no_bra
see-through wet_clothes lingerie garter_straps topless nude bondage pantyshot upskirt
censored mosaic_censoring bar_censor""".split())


def wh_search(q, page):
    params = {"q": q, "categories": "010", "purity": "100", "ratios": "9x16",
              "sorting": "favorites", "order": "desc", "page": page}
    for _ in range(3):
        try:
            r = S.get(WH, params=params, timeout=40)
            if r.status_code == 200:
                return r.json().get("data", [])
            if r.status_code == 429:
                time.sleep(5)
                continue
        except Exception as e:
            print("api error", e, flush=True)
        time.sleep(3)
    return []


def usable(p):
    try:
        w = int(p.get("dimension_x", 0)); h = int(p.get("dimension_y", 0))
    except Exception:
        return False
    if w < 1000 or h < 1700:
        return False
    ratio = w / h
    if not (0.53 <= ratio <= 0.60):
        return False
    names = set(t["name"].lower().replace(" ", "_") for t in p.get("tags", []))
    if names & BAD:
        return False
    return True


def dl(url):
    for _ in range(2):
        try:
            r = S.get(url, timeout=90)
            if r.status_code == 200 and len(r.content) > 80000:
                return r.content
        except Exception as e:
            print("dl error", e, flush=True)
        time.sleep(2)
    return None


def sheet(items, path, cols=5, tw=300, th=533):
    rows = max(1, (len(items) + cols - 1) // cols)
    im = Image.new("RGB", (cols * tw, rows * th), "white")
    d = ImageDraw.Draw(im)
    for i, it in enumerate(items):
        try:
            thumb = Image.open(it["file"]).convert("RGB")
        except Exception:
            continue
        thumb.thumbnail((tw - 6, th - 6))
        x = (i % cols) * tw; y = (i // cols) * th
        im.paste(thumb, (x + (tw - thumb.width) // 2, y + (th - thumb.height) // 2))
        d.rectangle([x, y, x + tw - 1, y + th - 1], outline="black")
        d.text((x + 5, y + 5), str(i), fill="red")
    im.save(path, quality=85)


def main():
    if os.path.isdir(CAND):
        shutil.rmtree(CAND)
    manifest = {}
    for key, query, name in SHOWS:
        posts = []
        for page in (1, 2, 3):
            batch = wh_search(query, page)
            posts.extend(batch)
            if len(batch) < 24:
                break
        good = [p for p in posts if usable(p)]
        good.sort(key=lambda p: -int(p.get("favorites", 0)))
        picked = []
        seen = set()
        for p in good:
            if p["id"] in seen:
                continue
            seen.add(p["id"])
            data = dl(p["path"])
            if not data:
                continue
            d = os.path.join(CAND, key)
            os.makedirs(d, exist_ok=True)
            fn = os.path.join(d, "%s.jpg" % p["id"])
            try:
                img = Image.open(io.BytesIO(data)); img.load()
                img = img.convert("RGB")
                img.save(fn, "JPEG", quality=92)
            except Exception:
                continue
            picked.append({"n": len(picked), "id": p["id"], "file": fn,
                            "w": int(p["dimension_x"]), "h": int(p["dimension_y"]),
                            "score": int(p.get("favorites", 0)),
                            "tags": " ".join(t["name"].lower().replace(" ", "_") for t in p.get("tags", [])),
                            "url": p["path"], "show": key, "name": name})
            if len(picked) >= 12:
                break
        if picked:
            sheet(picked, os.path.join(OUT, "sheet_%s.jpg" % key))
        manifest[key] = {"name": name, "tag": query, "total": len(posts),
                         "usable": len(good), "items": picked}
        print(key, len(posts), len(good), len(picked), flush=True)
    json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w"), indent=1)
    with open(os.path.join(OUT, "status.txt"), "w") as f:
        for k, v in manifest.items():
            f.write("%s total=%d usable=%d kept=%d\n" % (k, v["total"], v["usable"], len(v["items"])))


main()
