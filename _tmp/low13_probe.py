import time, requests
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json,image/*,*/*;q=0.8"}
TESTS = [("https://safebooru.donmai.us/posts.json", {"tags": "inuyasha", "limit": 3}),
         ("https://konachan.net/post.json", {"tags": "inuyasha", "limit": 3}),
         ("https://danbooru.donmai.us/posts.json", {"tags": "inuyasha rating:general", "limit": 3})]
for url, params in TESTS:
    t0 = time.time()
    try:
        r = requests.get(url, params=params, headers=UA, timeout=20)
        print("API", url, r.status_code, len(r.content), "%.1fs" % (time.time() - t0), flush=True)
        js = r.json()
        if js:
            for k in ("sample_url", "large_file_url", "file_url", "preview_file_url", "jpeg_url"):
                if js[0].get(k):
                    t1 = time.time()
                    try:
                        ri = requests.get(js[0][k], headers=UA, timeout=25)
                        print("  IMG", k, ri.status_code, len(ri.content) // 1024, "KB", "%.1fs" % (time.time() - t1), flush=True)
                    except Exception as e:
                        print("  IMG FAIL", k, type(e).__name__, flush=True)
                    break
    except Exception as e:
        print("API FAIL", url, type(e).__name__, str(e)[:80], flush=True)
