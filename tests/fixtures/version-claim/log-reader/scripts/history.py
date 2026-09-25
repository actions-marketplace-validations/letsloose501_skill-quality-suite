#!/usr/bin/env python3
"""Prints the last twenty commits that touched one path, following renames."""
import subprocess
import sys


def main():
    subprocess.run(["git", "log", "-n", "20", "--follow", "--oneline", "--", sys.argv[1]])


if __name__ == "__main__":
    main()
