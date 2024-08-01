#!/usr/bin/env python3

# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import argparse
import os
import subprocess

from .target_find_files import find_bicep_file


def images_pull(target, registry, repository, tag="latest"):

    assert target, "Target is required"
    assert registry, "Registry is required"
    if not repository:
        repository = os.path.splitext(find_bicep_file(target))[0]

    print(f"Logging into {registry}")
    subprocess.run(["az", "acr", "login", "--name", registry], check=True)

    print(f"Pulling images from {registry}")

    # Run the pull twice, once to get the output for the user, and once to
    # get the stderr to check missing images
    for stderr_val in (None, subprocess.PIPE):
        res = subprocess.run(
            ["docker", "compose", "pull"],
            env={
                **os.environ,
                "TARGET": os.path.realpath(target),
                "REGISTRY": registry,
                "REPOSITORY": repository,
                "TAG": tag,
            },
            stderr=stderr_val,
            cwd=target,
        )

    images_not_pulled = []
    for line in res.stderr.decode().split(os.linesep):
        if line.strip().startswith("docker compose build"):
            images_not_pulled.extend(line.split()[3:])

    if images_not_pulled:
        print(f'Pulled all images except: {" ".join(images_not_pulled)}')
    else:
        print("Pulled all images successfully")
    return images_not_pulled


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pull docker images from target")

    parser.add_argument(
        "target",
        help="Target directory",
        default=os.environ.get("TARGET"),
        nargs="?",  # aka Optional
        type=lambda path: os.path.abspath(os.path.expanduser(path)),
    )
    parser.add_argument(
        "--registry", help="Container Registry", default=os.environ.get("REGISTRY")
    )
    parser.add_argument(
        "--repository",
        help="Container Repository",
        default=os.environ.get("REPOSITORY"),
    )
    parser.add_argument(
        "--tag", help="Image Tag", default=os.environ.get("TAG") or "latest"
    )

    args = parser.parse_args()

    images_pull(
        target=args.target,
        registry=args.registry,
        repository=args.repository,
        tag=args.tag,
    )
