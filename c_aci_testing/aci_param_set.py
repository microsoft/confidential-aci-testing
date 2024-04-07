#!/usr/bin/env python3

import argparse
import os

from .target_find_files import find_bicep_param_file

def aci_param_set(file_path, key, value):

    with open(file_path, "r") as file:
        content = file.read().split(os.linesep)
    
    for i, line in enumerate(content):
        if line.startswith(f"param {key}="):
            content[i] = f"param {key}='{value}'"
            break
    
    with open(file_path, "w") as file:
        file.write(os.linesep.join(content))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate policies for target")

    parser.add_argument("target",
        help="Target directory", default=os.environ.get("TARGET"),
        nargs="?", # aka Optional
        type=lambda path: os.path.abspath(os.path.expanduser(path)))
    
    parser.add_argument("--parameter", 
        help="Parameter to set", required=True)
    
    args = parser.parse_args()

    param = args.param.split("=")
    aci_param_set(
        file=os.path.join(args.target, find_bicep_param_file(args.target)),
        key=param[0],
        value="=".join(param[1:]).replace(os.linesep, ""),
    )
