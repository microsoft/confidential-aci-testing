#!/usr/bin/env python3

# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import argparse
import os

from .target_find_files import find_bicep_param_file

def aci_param_set(file_path, key, value):

    print(f'Setting parameter {key} to {value[:50]}{"..." if len(value) > 50 else ""}')
    with open(file_path, "r") as file:
        content = file.read().split(os.linesep)

    for i, line in enumerate(content):
        if line.startswith(f"param {key}="):
            statement_end = i
            for start, end in (("[", "]"), ("{", "}")):
                if start in line:
                    for j in range(i, len(content)):
                        if end in content[j]:
                            statement_end = j
                            break
            del content[i:statement_end]
            content[i] = f"param {key}={value}"
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
