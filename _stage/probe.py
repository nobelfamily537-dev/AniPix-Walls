
import json, urllib.request, traceback
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept":"image/avif,image/webp,image/*,*/*;q=0.8","Accept-Language":"en-US,en;q=0.9"}
out={}
def get(url):
    req=urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()
def test(name,url,save=None):
    try:
        b=get(url); out[name]={"ok":True,"bytes":len(b)}
        if save: open(save,"wb").write(b)
    except Exception as e:
        out[name]={"ok":False,"err":str(e)[:150]}
try:
    j=json.loads(get("https://konachan.net/post.json"))
    out["konachan_api"]={"ok":True,"n":len(j)}
    if j: test("konachan_file", j[0]["file_url"], "_stage/k.jpg")
except Exception as e: out["konachan_api"]={"ok":False,"err":str(e)[:150]}
try:
    j=json.loads(get("https://safebooru.donmai.us/posts.json"))
    out["safebooru_api"]={"ok":True,"n":len(j)}
    if j:
        u=j[0].get("file_url") or j[0].get("large_file_url"); out["sb_url"]=u
        test("safebooru_file",u,"_stage/s.jpg")
except Exception as e: out["safebooru_api"]={"ok":False,"err":str(e)[:150]}
try:
    j=json.loads(get("https://danbooru.donmai.us/posts.json"))
    out["danbooru_api"]={"ok":True,"n":len(j)}
except Exception as e: out["danbooru_api"]={"ok":False,"err":str(e)[:150]}
try:
    j=json.loads(get("https://wallhaven.cc/api/v1/search"))
    d=j.get("data",[]); out["wallhaven_api"]={"ok":True,"n":len(d)}
    if d:
        out["wh_url"]=d[0]["path"]; test("wallhaven_file",d[0]["path"],"_stage/w.jpg")
except Exception as e: out["wallhaven_api"]={"ok":False,"err":str(e)[:150]}
test("reddit_direct","https://i.redd.it/kx9lfq2s3r8h1.jpeg","_stage/r.jpg")
try:
    h=get("https://www.pinterest.com/pin/9901863838022/").decode("utf-8","ignore")
    out["pinterest_page"]={"ok":True,"len":len(h),"has_og":"og:image" in h}
except Exception as e: out["pinterest_page"]={"ok":False,"err":str(e)[:150]}
json.dump(out, open("_stage/probe.json","w"), indent=1)
print(json.dumps(out)[:2000])
