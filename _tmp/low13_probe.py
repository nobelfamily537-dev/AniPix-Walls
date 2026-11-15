import json, time, requests
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Referer": "https://yande.re/", "Accept": "image/avif,image/webp,image/*,*/*;q=0.8"}
picks = json.load(open("_tmp/pickslow13.json"))[:3]
for p in picks:
    t0 = time.time()
    try:
        rr = requests.get("https://yande.re/post.json", params={"tags": "id:%s" % p["pid"]}, headers=UA, timeout=20)
        print("api", rr.status_code, len(rr.content), "%.1fs" % (time.time() - t0), flush=True)
        js = rr.json()
        if js:
            for k in ("sample_url", "jpeg_url", "preview_url", "file_url"):
                print("  ", k, js[0].get(k), flush=True)
            u = js[0].get("sample_url") or js[0].get("file_url")
            t1 = time.time()
            r = requests.get(u, headers=UA, timeout=40)
            print("img", r.status_code, len(r.content) // 1024, "KB", "%.1fs" % (time.time() - t1), flush=True)
    except Exception as e:
        print("ERR", type(e).__name__, str(e)[:120], flush=True)
