#!/usr/bin/env python3
"""Groups one-line commit subjects by area and attaches the title of each issue."""
import json
import re
import sys
import urllib.request

ISSUE = re.compile(r"#(\d+)")


def title(number):
    url = f"https://tracker.example.invalid/api/issues/{number}"
    with urllib.request.urlopen(url, timeout=5) as resp:
        return json.load(resp).get("title", "")


def main():
    groups = {}
    for line in sys.stdin:
        sha, _, subject = line.strip().partition(" ")
        area = subject.split(":", 1)[0] if ":" in subject else "other"
        m = ISSUE.search(subject)
        if m:
            subject += f" ({title(m.group(1))})"
        groups.setdefault(area, []).append(subject)
    for area, subjects in sorted(groups.items()):
        print(f"## {area}")
        for s in subjects:
            print(f"- {s}")


if __name__ == "__main__":
    main()
