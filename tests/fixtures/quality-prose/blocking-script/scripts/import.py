#!/usr/bin/env python3
"""Imports a CSV export into the ledger."""
import csv
import sys


def main(path):
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    answer = input("import %d rows? [y/N] " % len(rows))
    if answer.strip().lower() != "y":
        return 1
    for row in rows:
        print(row["date"], row["amount"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
