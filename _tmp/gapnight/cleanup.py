#!/usr/bin/env python3
import os, subprocess

def rm(path):
    if os.path.isdir(path):
        subprocess.run(["git", "rm", "-r", "-q", path], check=False)
    elif os.path.exists(path):
        subprocess.run(["git", "rm", "-q", path], check=False)

for f in ("anime/wpxe81c029e84.jpg", "anime/wpxe81c029e84_thumb.jpg"):
    rm(f)
for d in ("_tmp/gapnight/prev", "_tmp/gapnight/prev2", "_tmp/gapnight/prev3",
          "_tmp/gapnight/sheets", "_tmp/gapnight/sheets2", "_tmp/gapnight/sheets3"):
    rm(d)
for f in ("_tmp/gapnight/cands.json", "_tmp/gapnight/cands2.json", "_tmp/gapnight/cands3.json",
          "_tmp/gapnight/final_0.jpg", "_tmp/gapnight/added.json", "_tmp/gapnight/_probe.txt",
          "_tmp/gapnight/trigger_fetch.txt", "_tmp/gapnight/trigger_fetch2.txt",
          "_tmp/gapnight/trigger_fetch3.txt", "_tmp/gapnight/fix_trigger.txt",
          "_tmp/gapnight/fix2_trigger.txt"):
    rm(f)
print("cleanup done")
