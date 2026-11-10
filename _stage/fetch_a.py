#!/usr/bin/env python3
"""Phase A: gather portrait candidates for low-count series, save small previews."""
import json, os, io, hashlib, urllib.request, urllib.parse, concurrent.futures as cf
from PIL import Image

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "image/avif,image/webp,image/*,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9"}

SERIES = [
    {"tag": "sailor moon", "kon": ["bishoujo_senshi_sailor_moon", "sailor_moon"],
     "reddit": ["sailor moon", "sailormoon", "usagi"]},
    {"tag": "howls moving castle", "kon": ["howl's_moving_castle", "howl_no_ugoku_shiro"],
     "reddit": ["howl", "moving castle", "calcifer"]},
    {"tag": "my neighbor totoro", "kon": ["tonari_no_totoro"],
     "reddit": ["totoro"]},
    {"tag": "nausicaa", "kon": ["kaze_no_tani_no_nausicaa", "nausicaa"],
     "reddit": ["nausicaa", "nausicaä", "ohmu"]},
    {"tag": "clannad", "kon": ["clannad"],
     "reddit": ["clannad", "nagisa", "tomoyo", "kyou fujibayashi"]},
    {"tag": "fullmetal alchemist", "kon": ["fullmetal_alchemist", "fullmetal_alchemist:_brotherhood"],
     "reddit": ["fullmetal", "edward elric", "alphones", "alphonse", "fma"]},
    {"tag": "berserk", "kon": ["berserk"],
     "reddit": ["berserk", "guts", "griffith"]},
    {"tag": "fairy tail", "kon": ["fairy_tail"],
     "reddit": ["fairy tail", "fairytail", "erza", "natsu", "lucy heartfilia", "wendy marvel"]},
    {"tag": "bleach", "kon": ["bleach"],
     "reddit": ["bleach", "ichigo", "rukia", "aizen", "byakuya", "hitsugaya"]},
    {"tag": "neon genesis evangelion", "kon": ["neon_genesis_evangelion"],
     "reddit": ["evangelion", "eva unit", "asuka", "rei ayanami", "ayanami"]},
]

BAD_TAGS = ["text", "english_text", "watermark", "signature", "logo", "web_address",
            "artist_name", "speech_bubble", "comic", "multiple_views", "border",
            "letterboxed", "bad_anatomy", "bad_hands", "censored", "4koma", "sketch"]

MAX_PER_SERIES = 26


def get(url, timeout=90):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def konachan_posts(tag):
    posts = []
    for page in (1, 2, 3):
        qs = urllib.parse.urlencode({"tags": tag + " score:>=5", "limit": 100, "page": page})
        url = "https://konachan.net/post.json?" + qs
        try:
            posts += json.loads(get(url, 60))
        except Exception as e:
            print("konachan fail", tag, page, e)
            break
    return posts


def konachan_candidates(s):
    out = []
    for tag in s["kon"]:
        for p in konachan_posts(tag):
            try:
                w, h = int(p["width"]), int(p["height"])
            except Exception:
                continue
            if p.get("rating") != "s":
                continue
            if w < 900 or h / max(w, 1) < 1.35:
                continue
            tags = " ".join([p.get("tags", ""), p.get("tag_string_character", "")])
            if any(t in tags for t in BAD_TAGS):
                continue
            url = p["file_url"]
            if p.get("file_size", 0) > 9_000_000 and p.get("sample_url"):
                url = p["sample_url"]
            out.append({"url": url, "series": s["tag"], "source": "konachan",
                        "score": p.get("score", 0), "w": w, "h": h})
        if len(out) >= MAX_PER_SERIES * 2:
            break
    out.sort(key=lambda x: -x["score"])
    return out[:MAX_PER_SERIES]


def reddit_candidates(s, pool):
    out = []
    for v in pool:
        t = (v.get("title", "")).lower().replace("\u2019", "'")
        if not any(k in t for k in s["reddit"]):
            continue
        out.append({"url": v["url"], "series": s["tag"], "source": "reddit",
                    "score": v.get("score", 0), "title": v.get("title", "")[:90]})
    out.sort(key=lambda x: -x["score"])
    return out[:MAX_PER_SERIES]


def preview(item):
    key = hashlib.md5(item["url"].encode()).hexdigest()[:12]
    path = "_stage/p/%s.jpg" % key
    try:
        b = get(item["url"])
        im = Image.open(io.BytesIO(b)).convert("RGB")
        w, h = im.size
        if w < 800 or h < 1100 or h / max(w, 1) < 1.33:
            return None
        nw = 540
        im = im.resize((nw, int(h * nw / w)), Image.LANCZOS)
        im.save(path, "JPEG", quality=74, optimize=True)
        return {**item, "key": key, "w": w, "h": h}
    except Exception as e:
        print("preview fail", item["url"][:90], str(e)[:80])
        return None


def main():
    os.makedirs("_stage/p", exist_ok=True)
    pool = []
    if os.path.exists("_stage/reddit_pool.json"):
        pool = json.load(open("_stage/reddit_pool.json"))
    items = []
    seen = set()
    diag = {}
    for s in SERIES:
        rc = reddit_candidates(s, pool)
        kc = konachan_candidates(s)
        diag[s["tag"]] = {"reddit": len(rc), "konachan": len(kc)}
        cands = rc + kc
        for c in cands:
            if c["url"] in seen:
                continue
            seen.add(c["url"])
            items.append(c)
        print(s["tag"], len(cands))
    print("total candidates", len(items))
    with cf.ThreadPoolExecutor(10) as ex:
        kept = [r for r in ex.map(preview, items) if r]
    json.dump(kept, open("_stage/report_a.json", "w"))
    json.dump(diag, open("_stage/diag_a.json", "w"), indent=1)
    print(json.dumps(diag))
    print("kept", len(kept))


if __name__ == "__main__":
    import traceback
    try:
        main()
    except Exception:
        tb = traceback.format_exc()
        print(tb)
        open("_stage/err.txt", "w").write(tb)
