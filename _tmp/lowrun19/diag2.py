#!/usr/bin/env python3
import time, requests
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
      "Accept": "application/json,text/plain,*/*"}
TAGS = ["*vinland*", "*neverland*", "*kusuriya*", "*hajime_no_ippo*", "*kokuriko*", "*neko_no_onggaeshi*",
        "*ponyo*", "*kaze_tachinu*", "*mashle*", "*eighty_six*", "*god_eater*", "*porco*", "*gedo_senki*",
        "*chiikawa*", "thorfinn_(vinland_saga)", "vladilena_milize", "maomao_(kusuriya_no_hitorigoto)",
        "shinra_kusakabe", "mash_burnedead", "porco_rosso", "horikoshi_jirou", "fujinuma_satoru",
        "misaka_mikoto", "hinazuki_kayo", "studio_ghibli"]
for t in TAGS:
    try:
        r = requests.get("https://konachan.net/post.json", params={"tags": t + " rating:s", "limit": 100, "page": 1},
                         headers=UA, timeout=30)
        js = r.json()
        n = len(js)
        info = ""
        if n:
            p = js[0]
            info = "%sx%s | %s" % (p.get("width"), p.get("height"), " ".join(p.get("tags", "").split())[:110])
        print("%-34s posts=%-4s %s" % (t, n, info), flush=True)
    except Exception as e:
        print("%-34s ERR %s" % (t, type(e).__name__), flush=True)
    time.sleep(1.2)
