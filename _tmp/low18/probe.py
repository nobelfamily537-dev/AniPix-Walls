import requests, time
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"}
tests=[("konachan.net","https://konachan.net/post.json",{"tags":"sakurajima_mai rating:s","limit":5}),
       ("konachan.com","https://konachan.com/post.json",{"tags":"sakurajima_mai rating:s","limit":5}),
       ("yande.re","https://yande.re/post.json",{"tags":"sakurajima_mai rating:s","limit":5}),
       ("danbooru","https://danbooru.donmai.us/posts.json",{"tags":"sakurajima_mai rating:g","limit":5}),
       ("safebooru","https://safebooru.donmai.us/posts.json",{"tags":"sakurajima_mai","limit":5}),
       ("gelbooru","https://gelbooru.com/index.php",{"page":"dapi","s":"post","q":"index","json":"1","tags":"sakurajima_mai rating:safe","limit":5}),
       ]
for name,url,params in tests:
    t0=time.time()
    try:
        r=requests.get(url,params=params,headers=UA,timeout=15)
        body=r.text[:120].replace("\n"," ")
        n=-1
        try:
            j=r.json(); n=len(j if isinstance(j,list) else j.get("post",[]))
        except Exception: pass
        print(f"{name}: HTTP {r.status_code} n={n} {time.time()-t0:.1f}s :: {body}", flush=True)
    except Exception as e:
        print(f"{name}: ERR {type(e).__name__} {time.time()-t0:.1f}s", flush=True)
