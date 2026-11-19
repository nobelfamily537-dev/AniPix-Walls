#!/usr/bin/env python3
"""Gap-fill fetch (safebooru.org DAPI): portrait candidates for zero-coverage series."""
import io, json, os, re, time
import requests
from PIL import Image, ImageDraw

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
      "Accept": "application/json,text/html,*/*", "Referer": "https://safebooru.org/"}

OUT = "_tmp/gap20"
PREV = os.path.join(OUT, "prev")
SHEETS = os.path.join(OUT, "sheets")
os.makedirs(PREV, exist_ok=True)
os.makedirs(SHEETS, exist_ok=True)

SERIES = [
    ("jojo", ["jojo_no_kimyou_na_bouken", "kujo_jotaro", "dio_brando", "giorno_giovanna", "jolyne_cujoh", "higashikata_josuke"]),
    ("gurren", ["tengen_toppa_gurren_lagann", "yoko_littner", "kamina", "nia_teppelin"]),
    ("fruitsbasket", ["fruits_basket", "honda_tohru", "sohma_kyo", "sohma_yuki"]),
    ("bunnygirl", ["seishun_buta_yarou", "sakurajima_mai"]),
    ("oregairu", ["yahari_ore_no_seishun_love_comedy_wa_machigatteiru", "yukinoshita_yukino", "yuigahama_yui"]),
    ("chihayafuru", ["chihayafuru", "ayase_chihaya"]),
]

BAD = {"text", "english_text", "watermark", "signature", "artist_name", "speech_bubble", "comic",
       "4koma", "multiple_views", "character_sheet", "translated", "logo", "border", "frame",
       "letterboxed", "twitter_username", "web_address", "dated", "artist_logo", "english_commentary",
       "bad_id", "sketch", "monochrome", "greyscale", "partially_colored", "censored", "manga", "scan",
       "sample", "chibi", "comic_panel", "bikini", "swimsuit", "underwear", "lingerie", "panties",
       "bra", "cleavage", "no_bra", "see_through", "spread_legs", "large_breasts", "huge_breasts",
       "nude", "naked", "topless", "wet", "bed", "bottomless", "sideboob", "underboob", "photo",
       "photograph", "cosplay", "screencap", "screenshot", "reference_sheet", "upscaled",
       "jpeg_artifacts", "lowres", "real_world_location", "photo_background", "collage", "crossover",
       "vector", "lineart", "line_art", "blood", "gore", "guro", "game_cg", "cgi", "screen_capture",
       "redraw", "pantyhose", "loli", "child", "bad_anatomy", "bad_hands", "5girls", "6+girls",
       "4+girls", "3girls", "2girls", "multiple_girls", "multiple_boys", "duo", "trio", "group"}

API = "https://safebooru.org/index.php"


def get(params, timeout=25):
    for _ in range(2):
        try:
            r = requests.get(API, params=params, headers=UA, timeout=timeout)
            if r.status_code == 200:
                time.sleep(0.4)
                return r
            print("  HTTP", r.status_code, params.get("tags"), flush=True)
        except Exception as e:
            print("  ERR", type(e).__name__, params.get("tags"), flush=True)
        time.sleep(2)
    return None


def harvest():
    cands = {}
    for series, tags in SERIES:
        n = 0
        for tag in tags:
            for pid in (0, 1):
                r = get({"page": "dapi", "s": "post", "q": "index", "json": 1,
                         "tags": "%s rating:safe" % tag, "limit": 100, "pid": pid})
                if not r:
                    break
                try:
                    posts = r.json()
                except Exception:
                    break
                if not isinstance(posts, list) or not posts:
                    break
                print("%-13s %-52s p%d -> %d" % (series, tag, pid, len(posts)), flush=True)
                n += len(posts)
                for p in posts:
                    try:
                        w = int(p.get("width") or 0)
                        h = int(p.get("height") or 0)
                        if w < 850 or h < 1250:
                            continue
                        ratio = h / w
                        if ratio < 1.22:
                            continue
                        ts = set(re.split(r"\s+", (p.get("tags") or "").lower()))
                        if ts & BAD:
                            continue
                        if str(p.get("rating") or "s").lower() not in ("s", "safe"):
                            continue
                        url = p.get("file_url")
                        if not url:
                            continue
                        key = p.get("hash") or str(p.get("id"))
                        if key in cands:
                            cands[key]["series"].add(series)
                            continue
                        cands[key] = {"pid": "sb_%s" % p.get("id"), "hash": key,
                                      "series": {series}, "tag": tag, "url": url,
                                      "preview": p.get("sample_url") or url,
                                      "w": w, "h": h, "score": int(p.get("score") or 0),
                                      "tags": sorted(ts)}
                    except Exception:
                        continue
            if n > 400:
                break
        print("== %s pool %d" % (series, n), flush=True)
    return cands


def render(im, size=(270, 480)):
    w, h = im.size
    r = h / w
    t = size[1] / size[0]
    if r > t:
        nh = int(w * t)
        y = int((h - nh) * 0.15)
        im = im.crop((0, y, w, y + nh))
    else:
        nw = int(h / t)
        x = (w - nw) // 2
        im = im.crop((x, 0, x + nw, h))
    return im.resize(size, Image.LANCZOS)


def main():
    cands = harvest()
    print("total candidates", len(cands), flush=True)
    by_series = {}
    for c in cands.values():
        for s in c["series"]:
            by_series.setdefault(s, []).append(c)

    index = {}
    for series, _ in SERIES:
        lst = by_series.get(series, [])
        lst.sort(key=lambda c: -c["score"])
        lst = lst[:20]
        keep = []
        for i, c in enumerate(lst):
            try:
                r = requests.get(c["preview"], headers=UA, timeout=45)
                r.raise_for_status()
                im = Image.open(io.BytesIO(r.content)).convert("RGB")
            except Exception as e:
                print("  prev err", c["pid"], type(e).__name__, flush=True)
                continue
            fn = "%s/%s_%02d.jpg" % (PREV, series, i)
            render(im, (420, 747)).save(fn, "JPEG", quality=88)
            c2 = dict(c)
            c2["series"] = sorted(c["series"])
            c2["prev_file"] = fn
            c2["n"] = i
            keep.append(c2)
        index[series] = keep
        print(series, "kept", len(keep), flush=True)

        if keep:
            cols = 4
            rows = (len(keep) + cols - 1) // cols
            TW, TH = 270, 480
            sheet = Image.new("RGB", (cols * TW, rows * (TH + 26)), (18, 18, 22))
            d = ImageDraw.Draw(sheet)
            for j, c in enumerate(keep):
                im = Image.open(c["prev_file"]).resize((TW, TH), Image.LANCZOS)
                x = (j % cols) * TW
                y = (j // cols) * (TH + 26)
                sheet.paste(im, (x, y + 26))
                d.text((x + 6, y + 6), "%02d  sc%d  %dx%d" % (c["n"], c["score"], c["w"], c["h"]), fill=(255, 220, 90))
            sheet.save("%s/%s.jpg" % (SHEETS, series), "JPEG", quality=86)

    json.dump(index, open(os.path.join(OUT, "cands.json"), "w"), indent=1)
    print("done", flush=True)


if __name__ == "__main__":
    main()
