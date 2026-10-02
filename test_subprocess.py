import subprocess
import time

p = subprocess.Popen(["ls", "-la"])
time.sleep(1)
print("poll:", p.poll())
