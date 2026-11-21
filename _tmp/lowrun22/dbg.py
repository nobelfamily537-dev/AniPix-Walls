import requests, json
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36","Accept":"application/json"}
tests=[
 ("https://wallhaven.cc/api/v1/search",{"q":"beastars","categories":"010","purity":"100"}),
 ("https://wallhaven.cc/api/v1/search",{"q":"beastars","categories":"010","purity":"100","ratios":"9x16"}),
 ("https://wallhaven.cc/api/v1/search",{"q":"beastars","categories":"010","purity":"100","atleast":"1080x1920"}),
 ("https://wallhaven.cc/api/v1/search",{"q":"beastars anime","categories":"010","purity":"100"}),
 ("https://wallhaven.cc/api/v1/search",{"q":"bungou stray dogs","categories":"010","purity":"100"}),
 ("https://wallhaven.cc/api/v1/tag/beastars",{}),
]
for u,p in tests:
    try:
        r=requests.get(u,params=p,headers=UA,timeout=25)
        print(p, "->", r.status_code, r.text[:180].replace("\n"," "), flush=True)
    except Exception as e:
        print(p,"ERR",type(e).__name__, flush=True)
