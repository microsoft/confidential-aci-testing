#!/usr/bin/env python3

import argparse
import os
import subprocess

def images_push(target, registry, repository, tag):

    subprocess.run([
        "az", "acr", "login",
        "--name", registry,
    ])

    for dockerfile in os.listdir(target):
        if dockerfile.endswith(".Dockerfile"):
            image_name = os.path.splitext(dockerfile)[0]
            subprocess.run([
                    "docker", "push",
                    f'{registry}/{repository}/{image_name}:{tag}',
                ])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Push docker images from target")

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

    images_push(
        target=args.target,
        registry=args.registry,
        repository=args.repository,
        tag=args.tag,
    )
