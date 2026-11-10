import json, urllib.request, urllib.error

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
URLS = [
    "https://konachan.net/post.json",
    "https://konachan.net/post.json",
    "https://konachan.net/post.json",
    "https://konachan.com/post.json",
    "https://yande.re/post.json",
    "https://konachan.net/post.json",
]
out = {}
for u in URLS:
    try:
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=45) as r:
            b = r.read()
            out[u] = {"status": r.status, "len": len(b), "head": b[:150].decode("utf-8", "ignore")}
    except urllib.error.HTTPError as e:
        out[u] = {"status": e.code, "err": e.read()[:200].decode("utf-8", "ignore")}
    except Exception as e:
        out[u] = {"err": str(e)[:150]}
json.dump(out, open("_stage/diag_api.json", "w"), indent=1)
print(json.dumps(out)[:1500])
