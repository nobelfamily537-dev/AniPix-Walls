#!/usr/bin/env python3
"""Gap-fill night run: fetch portrait candidates for series with ZERO coverage."""
import io, json, os, re, time
import requests
from PIL import Image, ImageDraw, ImageOps, ImageFilter

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json,text/plain,*/*"}

OUT = "_tmp/gap20"
PREV = os.path.join(OUT, "prev")
SHEETS = os.path.join(OUT, "sheets")
os.makedirs(PREV, exist_ok=True)
os.makedirs(SHEETS, exist_ok=True)

SERIES = [
    ("jojo", ["jojo_no_kimyou_na_bouken", "kujo_jotaro", "dio_brando", "higashikata_josuke",
              "giorno_giovanna", "jolyne_cujoh", "stone_ocean", "golden_wind", "stardust_crusaders"]),
    ("gurren", ["tengen_toppa_gurren_lagann", "yoko_littner", "kamina", "simon_(ttgl)", "nia_teppelin"]),
    ("fruitsbasket", ["fruits_basket", "honda_tohru", "sohma_kyo", "sohma_yuki"]),
    ("bunnygirl", ["seishun_buta_yarou", "sakurajima_mai"]),
    ("towerofgod", ["tower_of_god", "twenty-fifth_bam", "khun_aguero_agnis", "endorsi_jahad",
                    "yuri_zahard", "rachel_(tower_of_god)"]),
    ("oregairu", ["yahari_ore_no_seishun_love_comedy_wa_machigatteiru", "yukinoshita_yukino",
                  "yuigahama_yui", "hikitani_hachiman"]),
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
       "redraw", "pantyhose", "loli", "child", "6+girls", "5girls", "bad_anatomy", "bad_hands",
       "4+girls", "3girls", "2girls", "multiple_girls", "multiple_boys", "1girl", "1boy"}

# 1girl/1boy removed below (too common) - handled separately
BAD -= {"1girl", "1boy"}

SOURCES = [
    ("safebooru", "https://safebooru.donmai.us/posts.json"),
    ("konachan", "https://konachan.net/post.json"),
    ("yande", "https://yande.re/post.json"),
]


def get(url, params, timeout=30):
    for _ in range(2):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout)
            if r.status_code == 200:
                time.sleep(0.4)
                return r
            print("  HTTP", r.status_code, url, flush=True)
        except Exception as e:
            print("  ERR", type(e).__name__, url, flush=True)
        time.sleep(2)
    return None


def harvest():
    all_c = {}
    for name, url in SOURCES:
        for series, tags in SERIES:
            for tag in tags:
                q = "rating:safe " + tag
                r = get(url, {"tags": q, "limit": 100, "page": 1})
                if not r:
                    continue
                try:
                    posts = r.json()
                except Exception:
                    continue
                print(name, series, tag, len(posts), flush=True)
                for p in posts:
                    try:
                        pid = "%s_%s" % (name, p.get("id"))
                        w = int(p.get("width") or 0)
                        h = int(p.get("height") or 0)
                        if w < 900 or h < 1100:
                            continue
                        ratio = h / max(w, 1)
                        if ratio < 1.15:
                            continue
                        tags_s = (p.get("tag_string") or p.get("tags") or "")
                        ts = set(re.split(r"[\s,]+", tags_s.lower()))
                        if ts & BAD:
                            continue
                        rating = p.get("rating")
                        if rating and rating not in ("s", "safe"):
                            continue
                        file_url = p.get("file_url")
                        sample = p.get("sample_url") or p.get("sample_file_url") or file_url
                        if not file_url:
                            continue
                        if name == "safebooru":
                            sample = p.get("sample_file_url") or file_url
                        score = int(p.get("score") or p.get("fav_count") or 0)
                        all_c[pid] = {"pid": pid, "series": series, "src": name, "tag": tag,
                                      "url": file_url, "preview": sample, "w": w, "h": h,
                                      "score": score, "tags": sorted(ts)[:60],
                                      "tall": ratio >= 1.55}
                    except Exception:
                        continue
    return all_c


def render(im, size=(270, 480)):
    w, h = im.size
    r = h / w
    tw, th = size
    t = th / tw
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
    print("total raw candidates", len(cands), flush=True)
    by_series = {}
    for c in cands.values():
        by_series.setdefault(c["series"], []).append(c)

    index = {}
    for series, lst in by_series.items():
        lst.sort(key=lambda c: (-int(c["tall"]), -c["score"]))
        lst = lst[:24]
        keep = []
        for i, c in enumerate(lst):
            try:
                r = requests.get(c["preview"], headers=UA, timeout=45)
                r.raise_for_status()
                im = Image.open(io.BytesIO(r.content)).convert("RGB")
            except Exception as e:
                print("  prev err", c["pid"], type(e).__name__, flush=True)
                continue
            fn = os.path.join(PREV, "%s_%02d.jpg" % (series, i))
            render(im, (420, 747)).save(fn, "JPEG", quality=88)
            c["prev_file"] = fn
            c["n"] = i
            keep.append(c)
        index[series] = keep
        print(series, len(keep), flush=True)

        # contact sheet 4 cols
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
            d.text((x + 6, y + 6), "%02d  %s  s%d" % (c["n"], c["src"][:4], c["score"]), fill=(255, 220, 90))
        sheet.save(os.path.join(SHEETS, series + ".jpg"), "JPEG", quality=86)

    json.dump(index, open(os.path.join(OUT, "cands.json"), "w"), indent=1)
    print("done", flush=True)


if __name__ == "__main__":
    main()
