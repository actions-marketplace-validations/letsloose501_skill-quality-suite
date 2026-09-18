#!/usr/bin/env python3
"""A stand-in for the routing runner, for the corpus only.

The real `evals/run_evals.py` compares every description in the tree against a set of
cases and, with `--live`, asks a model where a wording routes. This one asks nothing
and costs nothing: it reports a fixed failure, so the corpus can check that the suite
carries a runner's verdict through - and tells EV001 from EV003 - without a model in
the loop. What a stub cannot test is whether the real runner is right, and the corpus
does not pretend otherwise.
"""
import sys

live = "--live" in sys.argv
print("case `file this invoice` routed to `receipt-sorter`, expected `invoice-filer`"
      + (" (live judge)" if live else ""), file=sys.stderr)
sys.exit(1)
