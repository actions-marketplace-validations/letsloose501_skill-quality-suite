#!/usr/bin/env python3
"""Lists a folder. Every line here looks like indirection and is not."""
import argparse
import base64
import os
import sys


class Model:
    def eval(self):
        return "not the builtin"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("folder")
    parser.add_argument("--sort", default="size")
    args = parser.parse_args()
    # an attribute of the parsed arguments, by name - ordinary code
    for field in ("folder", "sort"):
        print(field, getattr(args, field))
    # a constant attribute with a default
    print("frozen:", getattr(sys, "frozen", False))
    # decoding data is not running it
    header = base64.b64decode("Zm9sZGVyLXJlcG9ydA==").decode()
    print(header, os.path.join(args.folder, "."), Model().eval())


if __name__ == "__main__":
    main()
