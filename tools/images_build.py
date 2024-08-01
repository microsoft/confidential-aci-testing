#!/usr/bin/env python3

# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import argparse
import os
import subprocess

from .target_find_files import find_bicep_file

def images_build(target, registry, repository, tag="latest", services_to_build=None):

    assert target, "Target is required"
    assert registry, "Registry is required"
    if not repository:
        repository = os.path.splitext(find_bicep_file(target))[0]

    build_command = ["docker", "compose", "build"]
    if services_to_build:
        build_command.extend(services_to_build)
        build_command.append("--with-dependencies")

    print(f"Buiding images for {registry}")
    subprocess.run(build_command,
        env={
            **os.environ,
            "TARGET": os.path.realpath(target),
            "REGISTRY": registry,
            "REPOSITORY": repository,
            "TAG": tag,
        },
        cwd=target,
        check=True,
    )

    print("Built all images successfully")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build docker images from target")

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

    images_build(
        target=args.target,
        registry=args.registry,
        repository=args.repository,
        tag=args.tag,
    )
