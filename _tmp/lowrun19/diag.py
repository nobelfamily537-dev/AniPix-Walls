#!/usr/bin/env python3
import json, time, requests
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
      "Accept": "application/json,text/plain,*/*"}
tests = [("https://konachan.net/post.json", "god_eater"),
         ("https://yande.re/post.json", "god_eater"),
         ("https://konachan.net/post.json", "enen_no_shouboutai"),
         ("https://yande.re/post.json", "enen_no_shouboutai"),
         ("https://konachan.net/post.json", "yakusoku_no_neverland"),
         ("https://yande.re/post.json", "yakusoku_no_neverland"),
         ("https://konachan.net/post.json", "kurenai_no_buta"),
         ("https://konachan.net/post.json", "eighty_six"),
         ("https://konachan.net/post.json", "mashle"),
         ("https://konachan.net/post.json", "vinland_saga"),
         ("https://konachan.net/post.json", "to_aru_kagaku_no_railgun"),
         ("https://konachan.net/post.json", "kaze_tachinu")]
for base, tag in tests:
    try:
        r = requests.get(base, params={"tags": tag + " rating:s", "limit": 100, "page": 1}, headers=UA, timeout=30)
        body = r.text[:160].replace("\n", " ")
        n = -1
        try:
            js = r.json()
            n = len(js)
            if n:
                p = js[0]
                body = "first: %sx%s rating=%s file=%s" % (p.get("width"), p.get("height"), p.get("rating"), str(p.get("file_url"))[:70])
        except Exception:
            pass
        print("%-40s %-26s status=%s len=%d posts=%s | %s" % (base.split("//")[1], tag, r.status_code, len(r.text), n, body), flush=True)
    except Exception as e:
        print(base, tag, "ERR", type(e).__name__, e, flush=True)
    time.sleep(1.5)
