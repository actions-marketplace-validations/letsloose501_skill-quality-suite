#!/usr/bin/env python3
"""Writes a YAML list of rows to an .xlsx file."""
import sys

import openpyxl
import requests
import yaml


def main():
    rows = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
    book = openpyxl.Workbook()
    for row in rows:
        book.active.append(list(row.values()))
    book.save(sys.argv[2])
    print(requests.__name__)


if __name__ == "__main__":
    main()
