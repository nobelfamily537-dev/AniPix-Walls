#!/usr/bin/env python3
import json, time
import requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"}

TESTS = [
    ("wh-haikyuu", "https://wallhaven.cc/api/v1/search", {"q": "haikyuu", "purity": "100", "categories": "010"}),
    ("wh-anime", "https://wallhaven.cc/api/v1/search",
     {"q": "haikyuu hinata", "purity": "100", "categories": "010", "ratios": "9x16,10x16"}),
    ("wh-ponyo", "https://wallhaven.cc/api/v1/search", {"q": "ponyo", "purity": "100", "categories": "010"}),
    ("wh-conan", "https://wallhaven.cc/api/v1/search",
     {"q": "detective conan", "purity": "100", "categories": "010"}),
    ("sb-haikyuu", "https://safebooru.org/index.php",
     {"page": "dapi", "s": "post", "q": "index", "tags": "haikyuu rating:safe", "json": "1", "limit": "100"}),
    ("sb-ponyo", "https://safebooru.org/index.php",
     {"page": "dapi", "s": "post", "q": "index", "tags": "gake_no_ue_no_ponyo", "json": "1", "limit": "100"}),
    ("ap-haikyuu", "https://anime-pictures.net/posts", {"api": "search_posts", "search_tag": "haikyuu"}),
    ("yande-ponyo", "https://yande.re/post.json", {"tags": "gake_no_ue_no_ponyo rating:s", "limit": 100}),
    ("yande-nausicaa", "https://yande.re/post.json", {"tags": "kaze_no_tani_no_nausicaa rating:s", "limit": 100}),
    ("yande-kusuriya", "https://yande.re/post.json", {"tags": "kusuriya_no_hitorigoto rating:s", "limit": 100}),
    ("yande-conan", "https://yande.re/post.json", {"tags": "detective_conan rating:s", "limit": 100}),
    ("yande-nanatsu", "https://yande.re/post.json", {"tags": "nanatsu_no_taizai rating:s", "limit": 100}),
    ("yande-howls", "https://yande.re/post.json", {"tags": "howl_no_ugoku_shiro rating:s", "limit": 100}),
    ("yande-initiald", "https://yande.re/post.json", {"tags": "initial_d rating:s", "limit": 100}),
    ("yande-gbc", "https://yande.re/post.json", {"tags": "girls_band_cry rating:s", "limit": 100}),
    ("yande-eminence", "https://yande.re/post.json",
     {"tags": "kage_no_jitsuryokusha_ni_naritakute! rating:s", "limit": 100}),
    ("yande-eminence2", "https://yande.re/post.json", {"tags": "kage_no_jitsuryokusha rating:s", "limit": 100}),
]

for name, url, params in TESTS:
    t0 = time.time()
    try:
        r = requests.get(url, params=params, headers=UA, timeout=30)
        n = -1
        js = None
        try:
            js = r.json()
            if isinstance(js, dict) and "data" in js:
                n = len(js["data"])
            elif isinstance(js, list):
                n = len(js)
            elif isinstance(js, dict) and "posts" in js:
                n = len(js["posts"])
        except Exception:
            pass
        print("%-16s %s n=%d %.1fs" % (name, r.status_code, n, time.time() - t0), flush=True)
        if n > 0:
            print("   sample:", str(js)[:400], flush=True)
    except Exception as e:
        print("%-16s ERR %s %.1fs" % (name, type(e).__name__, time.time() - t0), flush=True)
    time.sleep(1.2)
