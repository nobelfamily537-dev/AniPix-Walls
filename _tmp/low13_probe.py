import json, time, re, requests
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Referer": "https://yande.re/", "Accept": "image/avif,image/webp,image/*,*/*;q=0.8"}
p = json.load(open("_tmp/pickslow13.json"))[0]
u = p["url"]
m = re.search(r"/([0-9a-f]{32})/", u)
cands = []
if m:
    cands.append("https://files.yande.re/sample/%s/yande.re%%20%s%%20sample.jpg" % (m.group(1), p["pid"]))
cands.append(u)
for c in cands:
    t0 = time.time()
    try:
        r = requests.get(c, headers=UA, timeout=30)
        print("GET", r.status_code, len(r.content) // 1024, "KB", "%.1fs" % (time.time() - t0), c[:80], flush=True)
    except Exception as e:
        print("FAIL", type(e).__name__, "%.1fs" % (time.time() - t0), c[:80], flush=True)
