import json, os, subprocess
pids = json.load(open("_tmp/lowrun18/used_pids18.json"))
json.dump(pids, open("_tmp/lowrun18/used_pids.json", "w"))
for f in ("cands.json", "picks.json", "newids.json", "fetch.py", "fetch2.py", "process.py", "cleanup.py", "probe.py", "used_pids18.json"):
    p = os.path.join("_tmp/lowrun18", f)
    if os.path.exists(p):
        os.remove(p)
for w in os.listdir(".github/workflows"):
    if w.startswith("_tmp-lowrun18-"):
        os.remove(os.path.join(".github/workflows", w))
subprocess.run(["git", "add", "-A"], check=True)
subprocess.run(["git", "-c", "user.name=AniPix Bot", "-c", "user.email=nobelfamily537@gmail.com",
                "commit", "-m", "tmp: lowrun18 cleanup"], check=True)
subprocess.run(["git", "push"], check=True)
print("TIDY DONE")
