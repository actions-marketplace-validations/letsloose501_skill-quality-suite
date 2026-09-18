#!/usr/bin/env python3
"""The runner that must not run, for the corpus only.

Same position as any `evals/run_evals.py`: inside the tree the suite was pointed at.
The difference is that this case is run without `--trust-target`, which is how a
stranger's tree arrives - and a stranger's tree is the advertised use for `security`,
so a script in it getting executed because the tree was read is the failure mode.

It exits 0 and prints its own name. If the suite ever runs it again, the case stops
reporting EV006 and starts reporting nothing, and the corpus fails on the silence.
"""
import sys

print("run_evals.py in the target tree was executed", file=sys.stderr)
sys.exit(0)
