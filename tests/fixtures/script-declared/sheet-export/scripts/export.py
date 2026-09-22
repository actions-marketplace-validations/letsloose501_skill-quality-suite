#!/usr/bin/env python3
"""Writes a YAML list of rows to an .xlsx file. Every import here is declared somewhere."""
import sys

import openpyxl                  # `pip install openpyxl` in SKILL.md
import pandas                    # the frontmatter's `compatibility`
import yaml                      # installed as `pyyaml`, which SKILL.md names
from xlsxwriter import Workbook  # requirements.txt
from layout_rules import WIDTHS  # a module of this skill's own

import tabulate                  # an import line in references/layout.md

try:
    import colorama              # optional: the script runs without it
except ImportError:
    colorama = None


def main():
    rows = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
    frame = pandas.DataFrame(rows)
    frame.to_excel(sys.argv[2], engine="openpyxl")
    print(openpyxl.__name__, Workbook, WIDTHS, tabulate.__name__, colorama)


if __name__ == "__main__":
    main()
