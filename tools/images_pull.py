#!/usr/bin/env python3

# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import argparse
import os
import subprocess

from .target_find_files import find_bicep_file

def images_pull(target, registry, repository, tag="latest"):

    assert target is not None, "Target is required"
    assert registry is not None, "Registry is required"
    if repository is None:
        repository = os.path.splitext(find_bicep_file(target))[0]

    subprocess.run(["az", "acr", "login", "--name", registry])

    res = subprocess.run(["docker-compose", "pull"],
        env={
            **os.environ,
            "TARGET": os.path.realpath(target),
            "REGISTRY": registry,
            "REPOSITORY": repository,
            "TAG": tag,
        },
        cwd=target,
        capture_output=True,
        text=True,
    )
    for line in res.stderr.split(os.linesep):
        if line.strip().startswith("docker compose build"):
            return line.split()[3:]
    return []


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pull docker images from target")

    parser.add_argument("target",
        help="Target directory", default=os.environ.get("TARGET"),
        nargs="?", # aka Optional
        type=lambda path: os.path.abspath(os.path.expanduser(path)))
    parser.add_argument("--registry",
        help="Container Registry", default=os.environ.get("REGISTRY"))
    parser.add_argument("--repository",
        help="Container Repository", default=os.environ.get("REPOSITORY"))
    parser.add_argument("--tag",
        help="Image Tag", default=os.environ.get("TAG") or "latest")

    args = parser.parse_args()

    images_pull(
        target=args.target,
        registry=args.registry,
        repository=args.repository,
        tag=args.tag,
    )