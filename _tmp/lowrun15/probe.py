import requests, json
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36","Accept":"application/json,*/*"}
def t(name,url,params=None):
    try:
        r=requests.get(url,params=params,headers=UA,timeout=25)
        body=r.text[:300].replace("\n"," ")
        print(f"{name}: {r.status_code} len={len(r.text)} :: {body[:180]}",flush=True)
    except Exception as e:
        print(f"{name}: ERR {type(e).__name__}",flush=True)
t("wallhaven","https://wallhaven.cc/api/v1/search",{"q":"berserk","purity":"100","categories":"010"})
t("yande","https://yande.re/post.json",{"tags":"berserk rating:s","limit":5})
t("konachan.com","https://konachan.com/post.json",{"tags":"berserk rating:s","limit":5})
t("safebooru","https://safebooru.donmai.us/posts.json",{"tags":"berserk rating:g","limit":5})
t("gelbooru","https://gelbooru.com/index.php",{"page":"dapi","s":"post","q":"index","tags":"berserk","limit":5,"json":1})
t("zerochan","https://www.zerochan.net/Berserk",{"json":1,"l":5})
t("anime-pictures","https://anime-pictures.net/posts",{"search_tag":"berserk","lang":"en","json":1})
t("kitsu","https://kitsu.io/api/edge/anime",{"filter[text]":"berserk","page[limit]":1})
t("nekosapi","https://api.nekosapi.com/v4/images/random",{"limit":1})
