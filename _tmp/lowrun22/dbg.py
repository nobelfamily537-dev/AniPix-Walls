import requests, json
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36","Accept":"application/json,text/plain,*/*"}
def show(label, u, p, n=200):
    try:
        r=requests.get(u,params=p,headers=UA,timeout=25)
        t=r.text
        info=""
        try:
            j=r.json()
            if isinstance(j,dict) and "meta" in j: info="total=%s n=%s"%(j["meta"].get("total"),len(j.get("data",[])))
            elif isinstance(j,list): info="n=%s"%len(j)
            elif isinstance(j,dict) and "post" in j: info="n=%s"%len(j["post"])
            elif isinstance(j,dict): info=str(list(j)[:6])
        except Exception: info="non-json"
        print(label,"->",r.status_code,info,t[:120].replace("\n"," "),flush=True)
    except Exception as e:
        print(label,"ERR",type(e).__name__,flush=True)

W="https://wallhaven.cc/api/v1/search"
show("wh naruto ratios=portrait",W,{"q":"naruto","categories":"010","purity":"100","ratios":"portrait","atleast":"1080x1920"})
show("wh naruto ratios=9x16",W,{"q":"naruto","categories":"010","purity":"100","ratios":"9x16"})
show("wh naruto none",W,{"q":"naruto","categories":"010","purity":"100","atleast":"1080x1920","sorting":"favorites","order":"desc"})
show("danbooru beastars",'https://danbooru.donmai.us/posts.json',{"tags":"beastars rating:g","limit":3})
show("safebooru beastars",'https://safebooru.org/index.php',{"page":"dapi","s":"post","q":"index","limit":3,"tags":"beastars","json":"1"})
show("konachan beastars",'https://konachan.net/post.json',{"tags":"beastars","limit":3})
show("yandere beastars",'https://yande.re/post.json',{"tags":"beastars","limit":3})
show("gelbooru beastars",'https://gelbooru.com/index.php',{"page":"dapi","s":"post","q":"index","limit":3,"tags":"beastars","json":"1"})
