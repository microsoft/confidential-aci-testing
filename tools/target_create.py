#!/usr/bin/env python3


import argparse
import os
import subprocess


def target_create(target):

    if not os.path.exists(target):
        os.mkdir(target)

    if os.listdir(target):
        print(f"Target directory must be empty")
        return
    
    os.makedirs(target, exist_ok=True)
    example_path = os.environ.get("EXAMPLE_PATH")
    if example_path is None:
        example_path = os.path.realpath(
            os.path.join(os.path.dirname(__file__), "..", "test", "example")
        )
    
    # Copy the contents of example_path to target
    subprocess.run(["cp", "-r", example_path + "/.", target])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Security Policies for target")

    parser.add_argument("target",
        help="Target directory", default=os.environ.get("TARGET"),
        nargs="?", # aka Optional
        type=lambda path: os.path.abspath(os.path.expanduser(path)))

    args = parser.parse_args()

    target_create(args.target)
