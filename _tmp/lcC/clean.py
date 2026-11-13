import os, subprocess
P = [".github/workflows/_tmp-lc-d.yml", ".github/workflows/_tmp-lc-diag.yml",
     "_tmp/lc5/diag.py", "_tmp/lc5/rr.json", "_tmp/lc5/trigger.txt",
     "_tmp/lc7/d.py", "_tmp/lc7/trigger.txt",
     "_tmp/lcC/clean.py", "_tmp/lcC/trigger.txt", ".github/workflows/_tmp-lc-clean.yml"]
for p in P:
    if os.path.exists(p):
        subprocess.run(["git", "rm", "-q", "-f", p], check=False)
print("cleaned")
