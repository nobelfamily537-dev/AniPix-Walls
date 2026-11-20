import json,time,collections,requests
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36","Referer":"https://konachan.net/"}
TAGS=["megumin","aqua_(konosuba)","sakurajima_mai","kitagawa_marin","shiraishi_rin","zero_two_(darling_in_the_franxx)","mizuhara_chizuru","lucy_(cyberpunk)","yoko_littner","rem_(re:zero)","emilia_(re:zero)"]
BAD={"text","english_text","watermark","signature","artist_name","speech_bubble","comic","4koma","multiple_views","character_sheet","translated","logo","border","frame","letterboxed","twitter_username","web_address","dated","artist_logo","english_commentary","bad_id","sketch","monochrome","greyscale","partially_colored","censored","manga","scan","sample","food","chibi","comic_panel","bikini","swimsuit","underwear","lingerie","panties","bra","cleavage","no_bra","see_through","spread_legs","large_breasts","huge_breasts","ass","nude","naked","topless","wet","bed","bottomless","sideboob","underboob","photo","photograph","cosplay","screencap","screenshot","reference_sheet","upscaled","jpeg_artifacts","lowres","real_world_location","photo_background","collage","crossover","vector","lineart","line_art","blood","gore","guro","game_cg","cgi","anime_screencap","screen_capture","redraw","promotional_art","key_visual","poster","banner","album","cover","movie_poster","bad_pixiv_id","commentary","commentary_request","translation_request","character_request","artist_request","wide_image","variant_set","resolution_mismatch","partially_translated","chinese_text","korean_text","japanese_text","loli","child","aged_down","muscular","abs","sweat","tongue","pov","faceless_male","male_focus","greeting_card","calendar","sticker","meme","logo_parody","fake_screenshot","seiyuu","voice_actor","magazine","book","dakimakura","pillow","figure","toy","3d","real_life","photo_(medium)","cartoon","western","comic_book","greyscale_image","bikini_armor","bondage","restrained","gag","futanari","yaoi","yuri","kiss","nipples","areolae","pubic_hair","pussy","penis","sex","cum","hugging","tail","animal_ears","cosplay_photo","duplicate","cropped","huge_filesize","absurdres_placeholder"}
for tag in TAGS:
    for page in (1,2):
        try:
            r=requests.get("https://konachan.net/post.json",params={"tags":tag+" rating:s","limit":100,"page":page},headers=UA,timeout=25)
            posts=r.json() if r.status_code==200 else []
        except Exception as e:
            print(tag,"ERR",type(e).__name__,flush=True); posts=[]
        c=collections.Counter(); res=collections.Counter()
        for p in posts:
            w=p.get("width") or 0; h=p.get("height") or 0
            if not w or not h: c["nodim"]+=1; continue
            rt=h/w
            if set((p.get("tags") or "").split())&BAD: c["bad"]+=1; continue
            if p.get("rating")!="s": c["rating"]+=1; continue
            c["clean"]+=1
            if rt>=1.15: res["portrait"]+=1; res["p_ok" if (h>=1250 and w>=650) else "p_small"]+=1
            elif rt>=0.9: res["square"]+=1; res["s_ok" if h>=1450 else "s_small"]+=1
            else:
                res["landscape"]+=1
                res["l_ok" if (w>=2400 and h>=1300) else ("l_2200" if w>=2200 else "l_small")]+=1
        print(f"{tag} p{page}: n={len(posts)} {dict(c)} {dict(res)}",flush=True)
        time.sleep(0.8)
