#!/usr/bin/env python3

# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import argparse
import os

from .logging_window import LoggingWindow
from .target_find_files import find_bicep_file


def images_pull(target, registry, repository, tag="latest"):

    assert target, "Target is required"
    assert registry, "Registry is required"
    if not repository:
        repository = os.path.splitext(find_bicep_file(target))[0]

    with LoggingWindow(
        header=f"\033[92mPulling images for {target}\033[0m",
        prefix="\033[92m| \033[0m",
        max_lines=int(os.environ.get("LOG_LINES", 9999)),
    ) as run_subprocess:

        print(f"Logging into {registry}")
        run_subprocess(["az", "acr", "login", "--name", registry])

        print(f"Pulling images from {registry}")
        stdout, stderr = run_subprocess(
            ["docker-compose", "pull"],
            env={
                **os.environ,
                "TARGET": os.path.realpath(target),
                "REGISTRY": registry,
                "REPOSITORY": repository,
                "TAG": tag,
            },
            cwd=target,
        )

        images_not_pulled = []
        for line in stderr:
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
