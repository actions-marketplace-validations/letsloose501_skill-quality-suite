#!/usr/bin/env python3
"""Groups one-line commit subjects by the area named before the colon."""
import sys


def main():
    groups = {}
    for line in sys.stdin:
        sha, _, subject = line.strip().partition(" ")
        area = subject.split(":", 1)[0] if ":" in subject else "other"
        groups.setdefault(area, []).append(subject)
    for area, subjects in sorted(groups.items()):
        print(f"## {area}")
        for s in subjects:
            print(f"- {s}")


if __name__ == "__main__":
    main()
