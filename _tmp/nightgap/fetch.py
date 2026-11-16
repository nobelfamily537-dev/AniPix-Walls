import io, json, os, sys, time
import requests
from PIL import Image, ImageDraw

OUT = os.path.dirname(os.path.abspath(__file__))
CAND = os.path.join(OUT, "cand")
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (AniPixBot)"})
API = "https://safebooru.org/index.php"

SHOWS = [
    ("monogatari", "monogatari_series", "Monogatari"),
    ("gundam", "gundam", "Gundam"),
    ("gintama", "gintama", "Gintama"),
    ("kuroko", "kuroko_no_basket", "Kuroko no Basket"),
    ("digimon", "digimon_adventure", "Digimon Adventure"),
    ("eightsix", "86_eightysix", "86 Eighty Six"),
    ("dorohedoro", "dorohedoro", "Dorohedoro"),
    ("champloo", "samurai_champloo", "Samurai Champloo"),
    ("yurionice", "yuri!!!_on_ice", "Yuri on Ice"),
]

BAD = set("""english_text text watermark signature artist_name logo comic multiple_views
character_sheet sketch monochrome greyscale lineart chibi cosplay photo realistic 3d
border letterboxed speech_bubble translated bad_anatomy bad_hands lowres jpeg_artifacts
pixel_art collage scan screencap cropped partially_colored sensitive nsfw bikini swimsuit
underwear panties cleavage large_breasts huge_breasts spread_legs nipples ass no_bra
see-through wet_clothes lingerie garter_straps topless nude pussy penis sex cum bondage
pantyshot upskirt cameltoe sideboob underboob thick_thighs thighhighs_only
mosaic_censoring censored bar_censor what text_focus web_address twitter_username
patreon_username dated
game_cg official_art""".split())


def api(tags, pid):
    params = {"page": "dapi", "s": "post", "q": "index", "json": 1,
              "limit": 100, "pid": pid, "tags": tags}
    for attempt in range(3):
        try:
            r = S.get(API, params=params, timeout=40)
            if r.status_code == 200 and r.text.strip().startswith("["):
                return r.json()
        except Exception as e:
            print("api error", e, flush=True)
        time.sleep(2)
    return []


def collect(tag):
    posts = []
    for pid in range(0, 6):
        batch = api(f"{tag} rating:safe portrait", pid)
        if not batch:
            if pid == 0:
                batch = api(f"{tag} rating:safe", pid)
            if not batch:
                break
        posts.extend(batch)
        if len(batch) < 100:
            break
    return posts


def usable(p):
    try:
        w, h = int(p["width"]), int(p["height"])
    except Exception:
        return False
    if p.get("rating") != "safe":
        return False
    if h < 1500 or w < 800:
        return False
    ratio = w / h
    if not (0.50 <= ratio <= 0.76):
        return False
    tags = set(p.get("tags", "").split())
    if tags & BAD:
        return False
    if "text" in p.get("tags", ""):
        return False
    try:
        if int(p.get("score", 0)) < 4:
            return False
    except Exception:
        return False
    return True


def fetch(p):
    url = p.get("file_url") or ""
    if url.startswith("//"):
        url = "https:" + url
    elif url.startswith("/"):
        url = "https://safebooru.org" + url
    for attempt in range(2):
        try:
            r = S.get(url, timeout=60)
            if r.status_code == 200 and len(r.content) > 60000:
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
        x = (i % cols) * tw
        y = (i // cols) * th
        im.paste(thumb, (x + (tw - thumb.width) // 2, y + (th - thumb.height) // 2))
        d.rectangle([x, y, x + tw - 1, y + th - 1], outline="black")
        d.text((x + 5, y + 5), "%d  s%s" % (i, it["score"]), fill="red")
    im.save(path, quality=85)


def main():
    manifest = {}
    os.makedirs(CAND, exist_ok=True)
    for key, tag, name in SHOWS:
        posts = collect(tag)
        good = [p for p in posts if usable(p)]
        good.sort(key=lambda p: -int(p.get("score", 0)))
        picked = []
        seen = set()
        for p in good:
            if p["id"] in seen:
                continue
            seen.add(p["id"])
            data = fetch(p)
            if not data:
                continue
            d = os.path.join(CAND, key)
            os.makedirs(d, exist_ok=True)
            fn = os.path.join(d, "%s.jpg" % p["id"])
            try:
                img = Image.open(io.BytesIO(data))
                img.load()
                img = img.convert("RGB")
                img.save(fn, "JPEG", quality=92)
            except Exception:
                continue
            picked.append({"n": len(picked), "id": int(p["id"]), "file": fn,
                            "w": int(p["width"]), "h": int(p["height"]),
                            "score": int(p.get("score", 0)), "tags": p.get("tags", ""),
                            "url": p.get("file_url", ""), "show": key, "name": name})
            if len(picked) >= 10:
                break
        if picked:
            sheet(picked, os.path.join(OUT, "sheet_%s.jpg" % key))
        manifest[key] = {"name": name, "tag": tag, "total": len(posts),
                         "usable": len(good), "items": picked}
        print(key, len(posts), len(good), len(picked), flush=True)
    with open(os.path.join(OUT, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    with open(os.path.join(OUT, "status.txt"), "w") as f:
        for k, v in manifest.items():
            f.write("%s total=%d usable=%d kept=%d\n" % (k, v["total"], v["usable"], len(v["items"])))


main()
