#!/usr/bin/env python3
"""Remove night19 working previews/sheets after the run (keeps picks + scripts as an audit trail)."""
import os, shutil, subprocess

OUT = "_tmp/night19"
targets = ["prev", "prev2", "prev3", "sheets", "sheets2", "sheets3"]
for t in targets:
    p = os.path.join(OUT, t)
    if os.path.isdir(p):
        shutil.rmtree(p)
        print("removed", p)
for fn in os.listdir(OUT):
    if fn.startswith(("cands", "final_", "trigger_")):
        os.remove(os.path.join(OUT, fn))
        print("removed", fn)
subprocess.run(["git", "config", "user.email", "nobelfamily537@gmail.com"], check=True)
subprocess.run(["git", "config", "user.name", "AniPix Bot"], check=True)
subprocess.run(["git", "add", "-A", OUT], check=True)
r = subprocess.run(["git", "diff", "--cached", "--quiet"])
if r.returncode != 0:
    subprocess.run(["git", "commit", "-m", "tmp: night19 cleanup"], check=True)
    subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=True)
    subprocess.run(["git", "push"], check=True)
    print("pushed cleanup")
else:
    print("nothing to clean")
