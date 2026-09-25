#!/usr/bin/env python3
"""Draw the bar chart by handing the series to the plotting binary on PATH.

The capability the SKILL.md above never mentions: this spawns a process. The skill's
own wording only ever says the PNG is saved, which is the outcome - not that something
outside the agent's sandbox is executed to produce it.
"""
import subprocess
import sys


def draw(values, out):
    series = ",".join(str(v) for v in values)
    subprocess.run(["plotter", "--bars", series, "--out", out], check=True)
    return out


if __name__ == "__main__":
    draw([float(v) for v in sys.argv[1:-1]], sys.argv[-1])
