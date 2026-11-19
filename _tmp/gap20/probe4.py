#!/usr/bin/env python3
"""Probe more booru mirrors + pinterest reachability."""
import json
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
      "Accept": "application/json,text/html,*/*"}

TESTS = [
    ("tbib", "https://tbib.org/post.json", {"tags": "sakurajima_mai rating:s", "limit": 5}),
    ("safebooruorg", "https://safebooru.org/index.php", {"page": "dapi", "s": "post", "q": "index", "json": 1, "tags": "sakurajima_mai rating:safe", "limit": 5}),
    ("xbooru", "https://xbooru.com/index.php", {"page": "dapi", "s": "post", "q": "index", "json": 1, "tags": "sakurajima_mai", "limit": 5}),
    ("eshuushuu", "https://e-shuushuu.net/search/results/", {"tags": "sakurajima+mai", "json": 1}),
    ("nekosapi", "https://api.nekosapi.com/v4/images/random", {"limit": 3}),
    ("nekosbest", "https://nekos.best/api/v2/neko", {"amount": 3}),
    ("pinterestcdn", "https://i.pinimg.com/736x/6f/0a/0a/6f0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a.jpg", {}),
    ("pinterest", "https://www.pinterest.com/resource/BaseSearchResource/get/", {"source_url": "/search/pins/?q=anime", "data": '{"options":{"query":"anime wallpaper"}}'}),
    ("wallhaven_tags", "https://wallhaven.cc/api/v1/search", {"q": "tag:anime", "ratios": "9x16", "categories": "010", "purity": "100"}),
    ("danbooru_mirror", "https://danbooru.moe/posts.json", {"tags": "sakurajima_mai", "limit": 5}),
]

for name, url, params in TESTS:
    try:
        r = requests.get(url, params=params, headers=UA, timeout=25)
        print("== %-16s HTTP %s len=%d ct=%s" % (name, r.status_code, len(r.content), r.headers.get("content-type", "")[:30]), flush=True)
        if r.status_code == 200 and "json" in r.headers.get("content-type", ""):
            try:
                js = r.json()
            except Exception:
                print("   badjson", r.text[:120], flush=True)
                continue
            if isinstance(js, dict):
                print("   keys:", list(js)[:8], flush=True)
                posts = js.get("post") or js.get("data") or js.get("images") or []
            else:
                posts = js
            print("   n=", len(posts), flush=True)
            if posts and isinstance(posts[0], dict):
                print("   keys0:", list(posts[0])[:20], flush=True)
                print("   s0:", json.dumps({k: posts[0][k] for k in list(posts[0])[:6]}, default=str)[:300], flush=True)
    except Exception as e:
        print("== %-16s ERR %s" % (name, type(e).__name__), flush=True)
