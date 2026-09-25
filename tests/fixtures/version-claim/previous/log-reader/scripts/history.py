#!/usr/bin/env python3
"""Prints the last ten commits that touched one path."""
import subprocess
import sys


def main():
    subprocess.run(["git", "log", "-n", "10", "--oneline", "--", sys.argv[1]])


if __name__ == "__main__":
    main()
