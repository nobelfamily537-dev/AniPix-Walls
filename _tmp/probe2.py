import requests, json, re
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
def j(label,url,params=None):
    try:
        r=requests.get(url,params=params,headers=UA,timeout=60)
        print(f"--- {label} {r.status_code} len={len(r.content)}",flush=True)
        try:
            d=r.json()
        except Exception:
            print(r.text[:200],flush=True); return
        print("count",len(d),flush=True)
        for p in d[:3]:
            print({k:p.get(k) for k in ("id","width","height","score","sample_url","file_url","tags")},flush=True)
    except Exception as e:
        print(f"--- {label} ERR {e}",flush=True)
j("yande","https://yande.re/post.json",{"tags":"horimiya rating:s","limit":5})
j("yande-portrait","https://yande.re/post.json",{"tags":"horimiya rating:s ratio:9:16","limit":5})
j("konachan","https://konachan.net/post.json",{"tags":"horimiya rating:s","limit":5})
j("sb-debug","https://safebooru.org/index.php",{"page":"dapi","s":"post","q":"index","tags":"hori_kyouko sort:score:desc","limit":3,"pid":0})
r=requests.get("https://safebooru.org/index.php",params={"page":"dapi","s":"post","q":"index","tags":"hori_kyouko","limit":3,"pid":0},headers=UA,timeout=60)
print("SB RAW:", r.text[:800],flush=True)
