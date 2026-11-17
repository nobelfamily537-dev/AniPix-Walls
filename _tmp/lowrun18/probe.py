#!/usr/bin/env python3
import json, time
import requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"}

TESTS = [
    ("konachan", "https://konachan.net/post.json", {"tags": "haikyuu!! rating:s", "limit": 100}),
    ("yande", "https://yande.re/post.json", {"tags": "haikyuu!! rating:s", "limit": 100}),
    ("danbooru", "https://danbooru.donmai.us/posts.json", {"tags": "haikyuu!! rating:general", "limit": 100}),
    ("safebooru", "https://safebooru.donmai.us/posts.json", {"tags": "haikyuu!! rating:general", "limit": 100}),
    ("danbooru2", "https://danbooru.donmai.us/posts.json", {"tags": "kusuriya_no_hitorigoto", "limit": 20}),
    ("safebooru2", "https://safebooru.donmai.us/posts.json", {"tags": "gake_no_ue_no_ponyo", "limit": 20}),
    ("danbooru3", "https://danbooru.donmai.us/posts.json", {"tags": "howl_no_ugoku_shiro", "limit": 20}),
    ("danbooru4", "https://danbooru.donmai.us/posts.json", {"tags": "initial_d", "limit": 20}),
    ("safebooru3", "https://safebooru.donmai.us/posts.json", {"tags": "girls_band_cry", "limit": 20}),
    ("danbooru5", "https://danbooru.donmai.us/posts.json", {"tags": "kaze_no_tani_no_nausicaa", "limit": 20}),
    ("danbooru6", "https://danbooru.donmai.us/posts.json", {"tags": "nanatsu_no_taizai", "limit": 20}),
    ("danbooru7", "https://danbooru.donmai.us/posts.json", {"tags": "detective_conan", "limit": 20}),
    ("danbooru8", "https://danbooru.donmai.us/posts.json",
     {"tags": "kage_no_jitsuryokusha_ni_naritakute", "limit": 20}),
]

for name, url, params in TESTS:
    t0 = time.time()
    try:
        r = requests.get(url, params=params, headers=UA, timeout=30)
        n = -1
        try:
            js = r.json()
            n = len(js) if isinstance(js, list) else -2
        except Exception:
            pass
        print("%-12s %s n=%d %.1fs" % (name, r.status_code, n, time.time() - t0), flush=True)
        if n > 0:
            p = js[0]
            print("   keys:", sorted(p.keys())[:20], flush=True)
            print("   sample:", str({k: p.get(k) for k in ("id", "file_url", "large_file_url", "sample_url",
                                                          "preview_file_url", "width", "height", "rating",
                                                          "tag_string_general")})[:500], flush=True)
    except Exception as e:
        print("%-12s ERR %s %.1fs" % (name, type(e).__name__, time.time() - t0), flush=True)
    time.sleep(1.5)
