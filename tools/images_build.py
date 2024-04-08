#!/usr/bin/env python3

import argparse
import os
import subprocess

from .target_find_files import find_bicep_file

def images_build(target, registry, repository, tag="latest"):

    assert target is not None, "Target is required"
    assert registry is not None, "Registry is required"
    if repository is None:
        repository = os.path.splitext(find_bicep_file(target))[0]

    for dockerfile in os.listdir(target):
        if dockerfile.endswith(".Dockerfile"):
            image_name = os.path.splitext(dockerfile)[0]
            subprocess.run([
                "docker", "build",
                "-t", f'{registry}/{repository}/{image_name}:{tag}',
                "-f", f"{target}/{dockerfile}",
                target,
            ])


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