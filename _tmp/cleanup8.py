import os, shutil, subprocess
KEEP = {"cleanup8.py", "low_process8.py", "low_fetch8.py", "low_fetch9.py", "low_fetch10.py", "low_fetch11.py", "low_fetch12.py", "build_picks8.py", "pickslow8.json"}
for d in os.listdir("_tmp"):
    p = os.path.join("_tmp", d)
    if d.startswith("prevlow") and os.path.isdir(p):
        shutil.rmtree(p)
        print("rm dir", p)
    elif d.startswith("lowtrigger") or d.startswith("cleantrigger"):
        os.remove(p); print("rm", p)
    elif d.startswith("candlow") and d not in KEEP:
        os.remove(p); print("rm", p)
for wf in ["_tmp-lowfetch8.yml","_tmp-lowfetch9.yml","_tmp-lowfetch10.yml","_tmp-lowfetch11.yml","_tmp-lowfetch12.yml","_tmp-lowprocess8.yml","_tmp-cleanup8.yml"]:
    p = os.path.join(".github/workflows", wf)
    if os.path.exists(p):
        os.remove(p); print("rm", p)
subprocess.run(["git","add","-A"], check=True)
subprocess.run(["git","-c","user.name=AniPix Bot","-c","user.email=nobelfamily537@gmail.com","commit","-m","chore: clean up low-count run temp files"], check=True)
subprocess.run(["git","push"], check=True)
print("CLEANED")
