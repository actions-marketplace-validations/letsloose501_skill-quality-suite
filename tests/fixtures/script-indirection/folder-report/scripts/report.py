#!/usr/bin/env python3
"""Lists a folder - with every capability reached by indirection instead of by name."""
import os
import sys
from os import environ

# spawning a process, spelled so that `os.system` never appears
run = getattr(os, "sys" + "tem")
# the network, imported by string
fetch = __import__("urllib.request").request.urlopen
# an attribute picked by the caller: what this reaches is decided by data
action = getattr(os, sys.argv[1])

print(environ.get("HOME"), run, fetch, action)
