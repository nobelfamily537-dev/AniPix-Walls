import requests, json
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
def t(label, url, params=None):
    try:
        r=requests.get(url,params=params,headers=UA,timeout=60)
        print(f"--- {label} {r.status_code} len={len(r.content)} ct={r.headers.get('content-type')}",flush=True)
        print(r.text[:400].replace("\n"," "),flush=True)
    except Exception as e:
        print(f"--- {label} ERR {e}",flush=True)
t("sb-dapi","https://safebooru.org/index.php",{"page":"dapi","s":"post","q":"index","tags":"horimiya sort:score:desc","limit":5,"pid":0})
t("sb-json","https://safebooru.org/index.php",{"page":"dapi","s":"post","q":"index","tags":"horimiya","limit":3,"json":1})
t("db","https://danbooru.donmai.us/posts.json",{"tags":"horimiya rating:g","limit":3})
t("wh","https://wallhaven.cc/api/v1/search",{"q":"horimiya","categories":"010","purity":"100","ratios":"portrait","sorting":"favorites"})
t("gel","https://gelbooru.com/index.php",{"page":"dapi","s":"post","q":"index","tags":"horimiya","limit":3,"json":1})
