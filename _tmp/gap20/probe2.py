#!/usr/bin/env python3
"""Probe which image APIs are reachable from Actions and give portrait anime art."""
import json
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
      "Accept": "application/json,text/html,*/*", "Accept-Language": "en-US,en;q=0.9"}

TESTS = [
    ("wallhaven", "https://wallhaven.cc/api/v1/search", {"q": "yoko littner", "ratios": "9x16", "categories": "010", "purity": "100", "sorting": "toplist", "atleast": "1080x1920"}),
    ("danbooru", "https://danbooru.donmai.us/posts.json", {"tags": "yoko_littner rating:s", "limit": 5}),
    ("gelbooru", "https://gelbooru.com/index.php", {"page": "dapi", "s": "post", "q": "index", "json": 1, "tags": "yoko_littner rating:safe", "limit": 5}),
    ("animepictures", "https://anime-pictures.net/posts", {"api": 1, "search_tag": "yoko_littner", "page": 0}),
    ("safebooru2", "https://safebooru.donmai.us/posts.json", {"tags": "yoko_littner", "limit": 5}),
    ("nekosmoe", "https://nekos.moe/api/v1/images/search", {"limit": 3, "tags": "yoko"}),
    ("yandere2", "https://yande.re/post.json", {"tags": "yoko_littner rating:s", "limit": 5}),
    ("konachancom", "https://konachan.com/post.json", {"tags": "yoko_littner rating:s", "limit": 5}),
]

for name, url, params in TESTS:
    try:
        r = requests.get(url, params=params, headers=UA, timeout=25)
        print("== %-14s HTTP %s len=%d" % (name, r.status_code, len(r.content)), flush=True)
        if r.status_code == 200:
            try:
                js = r.json()
            except Exception:
                print("   not json:", r.text[:200], flush=True)
                continue
            if isinstance(js, dict):
                print("   keys:", list(js)[:8], flush=True)
                posts = js.get("data") or js.get("post") or js.get("images") or []
            else:
                posts = js
            print("   n=", len(posts), flush=True)
            if posts:
                p = posts[0]
                if isinstance(p, dict):
                    print("   sample keys:", list(p)[:18], flush=True)
                    print("   sample:", json.dumps({k: p[k] for k in list(p)[:8]}, default=str)[:400], flush=True)
    except Exception as e:
        print("== %-14s ERR %s" % (name, type(e).__name__), flush=True)
