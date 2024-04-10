#!/usr/bin/env python3

# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.


import argparse
import os
import subprocess


def target_add_python(target):

    # Create a virtual environment with this python package installed
    subprocess.run([
        "python3", "-m", "venv", f"{target}/.venv",
    ], check=True)
    subprocess.run([
        f"{target}/.venv/bin/pip", "install", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
    ], check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Security Policies for target")

    parser.add_argument("target",
        help="Target directory", default=os.environ.get("TARGET"),
        nargs="?", # aka Optional
        type=lambda path: os.path.abspath(os.path.expanduser(path)))

    args = parser.parse_args()

    target_add_python(args.target)
