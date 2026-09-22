# /// script
# requires-python = ">=3.9"
# dependencies = ["matplotlib"]
# ///
"""Draws the rows as a bar chart. Run with `uv run scripts/chart.py`."""
import sys

import matplotlib

print(matplotlib.__name__, sys.argv[1:])
