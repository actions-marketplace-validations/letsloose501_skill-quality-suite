#!/usr/bin/env python3
"""Checks a status endpoint and prints whether it answered."""
import os
import subprocess

import requests


def main():
    api_key = os.environ.get("STATUS_API_KEY")
    resp = requests.get("https://status.example.invalid/health",
                        headers={"Authorization": api_key})
    subprocess.run(["echo", str(resp.status_code)])


if __name__ == "__main__":
    main()
