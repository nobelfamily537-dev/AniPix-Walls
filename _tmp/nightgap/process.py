import json, os, random
import requests
from PIL import Image
from io import BytesIO

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SEL = json.load(open(os.path.join(HERE, "selection.json")))
DATE = "2026-11-16"
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (AniPixBot)"})


def fit(im, size, cut=0.0):
    im = im.convert("RGB")
    w, h = im.size
    if cut:
        im = im.crop((0, 0, w, int(h * (1 - cut))))
        w, h = im.size
    target = size[0] / size[1]
    if w / h > target:
        nw = int(h * target)
        left = (w - nw) // 2
        im = im.crop((left, 0, left + nw, h))
    else:
        nh = int(w / target)
        top = max(0, int((h - nh) * 0.3))
        im = im.crop((0, top, w, top + nh))
    return im.resize(size, Image.LANCZOS)


def main():
    wp_path = os.path.join(ROOT, "wallpapers.json")
    data = json.load(open(wp_path))
    added = []
    for pick in SEL:
        try:
            r = S.get(pick["src"], timeout=120)
            r.raise_for_status()
            im = Image.open(BytesIO(r.content))
            im.load()
        except Exception as e:
            print("download failed", pick["src"], e)
            continue
        cat = pick["cat"]
        wid = "wpx" + "".join(random.choice("0123456789abcdef") for _ in range(10))
        folder = os.path.join(ROOT, cat)
        os.makedirs(folder, exist_ok=True)
        full = fit(im, (1080, 1920), pick.get("cut", 0))
        full.save(os.path.join(folder, wid + ".jpg"), "JPEG", quality=95, optimize=True)
        thumb = fit(im, (360, 640), pick.get("cut", 0))
        thumb.save(os.path.join(folder, wid + "_thumb.jpg"), "JPEG", quality=80, optimize=True)
        base = "https://raw.githubusercontent.com/nobelfamily537-dev/AniPix-Walls/main/%s/" % cat
        entry = {"id": wid, "thumb": base + wid + "_thumb.jpg",
                 "full": base + wid + ".jpg", "alt": base + wid + ".jpg",
                 "tags": pick["tags"], "date": DATE}
        data["categories"][cat].insert(0, entry)
        added.append((cat, wid, pick["show"], pick["id"]))
        print("ok", cat, wid, pick["show"], pick["id"], flush=True)
    data["version"] = int(data.get("version", 0)) + 1
    data["last_updated"] = DATE
    with open(wp_path, "w") as f:
        json.dump(data, f, ensure_ascii=False)
    print("added", len(added), "version", data["version"])


main()
