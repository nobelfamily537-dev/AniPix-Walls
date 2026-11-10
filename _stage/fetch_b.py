#!/usr/bin/env python3
"""Phase B: turn picks into final wallpapers and update wallpapers.json."""
import json, io, os, datetime, urllib.request
from PIL import Image

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "image/avif,image/webp,image/*,*/*;q=0.8"}
DATE = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d")
RAW = "https://raw.githubusercontent.com/nobelfamily537-dev/AniPix-Walls/main"


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def crop_916(im, yfocus=0.32):
    w, h = im.size
    t = 9 / 16
    if w / h > t:
        nw = int(h * t)
        x = (w - nw) // 2
        return im.crop((x, 0, x + nw, h))
    nh = int(w / t)
    y = int((h - nh) * yfocus)
    return im.crop((0, y, w, y + nh))


def main():
    data = json.load(open("wallpapers.json", encoding="utf-8"))
    picks = json.load(open("_stage/picks.json"))
    have_ids = {e["id"] for c in data["categories"].values() for e in c}
    have_full = {e.get("full", "") for c in data["categories"].values() for e in c}
    added, skipped = [], []
    for p in picks:
        wid, cat = p["id"], p["category"]
        if wid in have_ids:
            skipped.append((wid, "dup id"))
            continue
        try:
            im = Image.open(io.BytesIO(get(p["url"]))).convert("RGB")
            if im.width < 800 or im.height < 1100:
                skipped.append((wid, "small %sx%s" % im.size))
                continue
            im = crop_916(im)
            im = im.resize((1080, 1920), Image.LANCZOS)
            os.makedirs(cat, exist_ok=True)
            im.save("%s/%s.jpg" % (cat, wid), "JPEG", quality=95, optimize=True, progressive=True)
            im.resize((360, 640), Image.LANCZOS).save(
                "%s/%s_thumb.jpg" % (cat, wid), "JPEG", quality=80, optimize=True, progressive=True)
            full = "%s/%s/%s.jpg" % (RAW, cat, wid)
            entry = {"id": wid, "thumb": "%s/%s/%s_thumb.jpg" % (RAW, cat, wid),
                     "full": full, "alt": full, "tags": p["tags"], "date": DATE}
            data["categories"][cat].insert(0, entry)
            for t in [x.strip() for x in p["tags"].split(",") if x.strip()]:
                data["tags"].setdefault(t, [])
                if wid not in data["tags"][t]:
                    data["tags"][t].insert(0, wid)
            have_ids.add(wid)
            added.append((wid, cat, p["series"]))
        except Exception as e:
            skipped.append((wid, str(e)[:80]))
    data["version"] = int(data.get("version", 1)) + 1
    data["last_updated"] = DATE
    json.dump(data, open("wallpapers.json", "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    json.dump({"added": added, "skipped": skipped, "date": DATE},
              open("_stage/report_b.json", "w"), indent=1)
    print("added", len(added), "skipped", len(skipped))
    print(json.dumps(skipped)[:600])


if __name__ == "__main__":
    import traceback
    try:
        main()
    except Exception:
        tb = traceback.format_exc()
        print(tb)
        open("_stage/err_b.txt", "w").write(tb)
