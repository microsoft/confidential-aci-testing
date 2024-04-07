#!/usr/bin/env python3


import argparse
import os
import subprocess
from importlib.resources import files


def target_create(target, name):

    os.makedirs(target, exist_ok=True)
    if os.listdir(target):
        print(f"Target directory must be empty")
        return
    
    example_path = os.environ.get("EXAMPLE_PATH")
    if example_path is None:
        example_path = str(files(__name__).joinpath("../test/example"))
    
    # Copy the contents of example_path to target
    subprocess.run(["cp", "-r", example_path + "/.", target])

    # Rename the files to match the target name
    os.rename(
        os.path.join(target, "example.bicep"),
        os.path.join(target, f"{name}.bicep"),
    )
    os.rename(
        os.path.join(target, "example.bicepparam"),
        os.path.join(target, f"{name}.bicepparam"),
    )
    with open(os.path.join(target, f"{name}.bicepparam"), "r") as f:
        lines = f.readlines()
    lines[0] = f"using './{name}.bicep'\n"
    with open(os.path.join(target, f"{name}.bicepparam"), "w") as f:
        f.writelines(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Security Policies for target")

    parser.add_argument("target",
        help="Target directory", default=os.environ.get("TARGET"),
        nargs="?", # aka Optional
        type=lambda path: os.path.abspath(os.path.expanduser(path)))

    parser.add_argument("--name", "-n", help="The name of the new target", required=True)

    args = parser.parse_args()

    target_create(args.target, args.name)
