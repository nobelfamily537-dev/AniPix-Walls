#!/usr/bin/env python3
"""Probe extra image sources (round 2)."""
import json, re, time, urllib.parse
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"}
Q = "gotoubun no hanayome"


def show(tag, r, n=None):
    body = r.text[:200].replace("\n", " ") if r is not None else ""
    print("P %-22s %s n=%s %s" % (tag, getattr(r, "status_code", "ERR"), n, body), flush=True)


# 1 konachan variants
for tg in ("gotoubun_no_hanayome", "gotoubun", "go-toubun_no_hanayome"):
    try:
        r = requests.get("https://konachan.net/post.json", params={"tags": tg, "limit": 100}, headers=UA, timeout=25)
        js = r.json() if r.status_code == 200 else None
        show("konachan:" + tg, r, len(js) if isinstance(js, list) else "notlist")
    except Exception as e:
        print("P konachan:%s %s" % (tg, type(e).__name__), flush=True)

# 2 yande.re
try:
    r = requests.get("https://yande.re/post.json", params={"tags": "gotoubun_no_hanayome", "limit": 100}, headers=UA, timeout=40)
    js = r.json() if r.status_code == 200 else None
    show("yande", r, len(js) if isinstance(js, list) else "notlist")
except Exception as e:
    print("P yande %s" % type(e).__name__, flush=True)

# 3 safebooru.org
try:
    r = requests.get("https://safebooru.org/index.php",
                     params={"page": "dapi", "s": "post", "q": "index", "tags": "gotoubun_no_hanayome",
                             "limit": 100, "json": 1}, headers=UA, timeout=30)
    n = -1
    try:
        n = len(r.json())
    except Exception:
        n = "nonjson"
    show("safebooru.org", r, n)
except Exception as e:
    print("P safebooru %s" % type(e).__name__, flush=True)

# 4 zerochan
for path in ("Gotoubun+no+Hanayome", "Go-Toubun+no+Hanayome"):
    try:
        r = requests.get("https://www.zerochan.net/" + path, params={"json": 1}, headers=UA, timeout=30)
        n = -1
        try:
            js = r.json()
            n = len(js.get("items", js)) if isinstance(js, (dict, list)) else "?"
        except Exception:
            n = "nonjson"
        show("zerochan:" + path[:18], r, n)
    except Exception as e:
        print("P zerochan %s" % type(e).__name__, flush=True)

# 5 anime-pictures.net
try:
    r = requests.get("https://anime-pictures.net/posts",
                     params={"search_tag": "gotoubun_no_hanayome", "json": 1, "page": 0}, headers=UA, timeout=30)
    n = -1
    try:
        js = r.json()
        n = len(js.get("posts", js))
    except Exception:
        n = "nonjson"
    show("anime-pictures", r, n)
except Exception as e:
    print("P anime-pictures %s" % type(e).__name__, flush=True)

# 6 bing images async
try:
    r = requests.get("https://www.bing.com/images/async",
                     params={"q": Q + " anime wallpaper 1080x1920", "first": 1, "count": 35, "mkt": "en-US"},
                     headers=UA, timeout=30)
    murls = re.findall(r'murl&quot;:&quot;(.*?)&quot;', r.text)
    show("bing-async", r, len(murls))
    if murls:
        print("   sample:", murls[0][:110], flush=True)
except Exception as e:
    print("P bing %s" % type(e).__name__, flush=True)

# 7 duckduckgo images
try:
    s = requests.Session()
    h = s.get("https://duckduckgo.com/", params={"q": Q + " wallpaper"}, headers=UA, timeout=30)
    m = re.search(r'vqd=["\']?([\d-]+)', h.text) or re.search(r'vqd=([\d-]+)&', h.text)
    if not m:
        print("P ddg no-vqd", flush=True)
    else:
        r = s.get("https://duckduckgo.com/i.js",
                  params={"l": "us-en", "o": "json", "q": Q + " wallpaper", "vqd": m.group(1), "f": ",,,", "p": "1"},
                  headers=dict(UA, Referer="https://duckduckgo.com/"), timeout=30)
        n = -1
        try:
            n = len(r.json().get("results", []))
        except Exception:
            n = "nonjson"
        show("ddg", r, n)
except Exception as e:
    print("P ddg %s" % type(e).__name__, flush=True)

# 8 wallhaven tag: syntax
for q in ("tag:gotoubun_no_hanayome", "gotoubun"):
    try:
        r = requests.get("https://wallhaven.cc/api/v1/search",
                         params={"q": q, "categories": "010", "purity": "100", "ratios": "9x16,10x16,2x3"}, headers=UA, timeout=25)
        js = r.json() if r.status_code == 200 else {}
        print("P wallhaven:%s %s n=%s" % (q, r.status_code, len(js.get("data") or [])), flush=True)
    except Exception as e:
        print("P wallhaven %s" % type(e).__name__, flush=True)
    time.sleep(0.5)

# 9 pinterest search (json resource)
try:
    data = {"options": {"query": Q + " wallpaper", "scope": "pins", "page_size": 25}, "context": {}}
    r = requests.get("https://www.pinterest.com/resource/BaseSearchResource/get/",
                     params={"source_url": "/search/pins/?q=" + urllib.parse.quote(Q),
                             "data": json.dumps(data)},
                     headers=dict(UA, Accept="application/json"), timeout=30)
    n = -1
    try:
        n = len(json.dumps(r.json()))
    except Exception:
        n = "nonjson"
    show("pinterest", r, n)
except Exception as e:
    print("P pinterest %s" % type(e).__name__, flush=True)
