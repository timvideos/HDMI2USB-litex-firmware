import os
import sys
import subprocess

current_path = os.path.dirname(os.path.realpath(__file__))

# cleanup
os.chdir("C:\Python34\Lib\site-packages")
subprocess.call("rm -rf misoc*")
subprocess.call("rm -rf migen*")
subprocess.call("rm -rf lite*")

# pull
for d in ["migen", "misoc", "liteeth", "litescope", "fx2lib"]:
	os.chdir(os.path.join(current_path, d))
	subprocess.call("git pull")

# install
for d in ["migen", "misoc", "liteeth", "litescope"]:
	os.chdir(os.path.join(current_path, d))
	subprocess.call("python3 setup.py install")
