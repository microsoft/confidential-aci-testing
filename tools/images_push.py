#!/usr/bin/env python3

# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import argparse
import os
import subprocess

def images_push(target, registry, tag):

    subprocess.run(["az", "acr", "login", "--name", registry])

    subprocess.run(["docker-compose", "push"],
        env={
            **os.environ,
            "REGISTRY": registry,
            "TAG": tag,
        },
        cwd=target,
        check=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Push docker images from target")

    parser.add_argument("target",
        help="Target directory", default=os.environ.get("TARGET"),
        nargs="?", # aka Optional
        type=lambda path: os.path.abspath(os.path.expanduser(path)))
    parser.add_argument("--registry",
        help="Container Registry", default=os.environ.get("REGISTRY"))
    parser.add_argument("--tag",
        help="Image Tag", default=os.environ.get("TAG") or "latest")

    args = parser.parse_args()

    images_push(
        target=args.target,
        registry=args.registry,
        tag=args.tag,
    )
