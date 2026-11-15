import requests
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36","Accept":"application/json,*/*"}
def wh(label,**p):
    try:
        r=requests.get("https://wallhaven.cc/api/v1/search",params=p,headers=UA,timeout=25)
        js=r.json() if r.headers.get("content-type","").startswith("application/json") else {}
        d=js.get("data") or []
        print(f"WH {label}: {r.status_code} n={len(d)} meta={js.get('meta')} err={str(js.get('error'))[:80]}",flush=True)
    except Exception as e:
        print(f"WH {label}: ERR {type(e).__name__} {e}",flush=True)
def kc(label,url,tags,limit=100):
    try:
        r=requests.get(url,params={"tags":tags,"limit":limit},headers=UA,timeout=25)
        js=r.json() if r.text.startswith("[") else []
        print(f"{label}: {r.status_code} n={len(js)}",flush=True)
    except Exception as e:
        print(f"{label}: ERR {type(e).__name__}",flush=True)

wh("plain",q="berserk",purity="100",categories="010")
wh("sort",q="berserk",purity="100",categories="010",sorting="toplist",order="desc",page=1)
wh("atleast",q="berserk",purity="100",categories="010",sorting="toplist",order="desc",page=1,atleast="1200x1200")
wh("k8",q="kaiju no. 8",purity="100",categories="010",sorting="toplist",page=1)
wh("k8b",q="kaiju",purity="100",categories="010",sorting="toplist",page=1)
wh("souleater",q="soul eater",purity="100",categories="010",sorting="toplist",page=1)
kc("konachan.com soul_eater","https://konachan.com/post.json","soul_eater rating:s")
kc("konachan.com maka","https://konachan.com/post.json","maka_albarn rating:s")
kc("konachan.com berserk","https://konachan.com/post.json","berserk rating:s")
kc("konachan.com guts","https://konachan.com/post.json","guts_(berserk) rating:s")
kc("yande soul_eater","https://yande.re/post.json","soul_eater rating:s")
kc("yande nanatsu","https://yande.re/post.json","nanatsu_no_taizai rating:s")
kc("konachan.net nanatsu","https://konachan.net/post.json","nanatsu_no_taizai rating:s")
kc("konachan.net meliodas","https://konachan.net/post.json","meliodas rating:s")
kc("konachan.net laios","https://konachan.net/post.json","laios_touden rating:s")
kc("konachan.net kafka","https://konachan.net/post.json","hibino_kafka rating:s")
kc("konachan.net sakura_haruka","https://konachan.net/post.json","sakura_haruka rating:s")
kc("konachan.net nina","https://konachan.net/post.json","ishigaki_nina rating:s")
