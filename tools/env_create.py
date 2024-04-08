#!/usr/bin/env python3

import argparse


def env_create(out=None):
    env = \
"""# Core Environment Variables
export SUBSCRIPTION=
export RESOURCE_GROUP=
export REGISTRY=
export MANAGED_IDENTITY=
export LOCATION=
export GITHUB_ORG=
export GITHUB_REPO=

# Per Target Options that can also be set at runtime
# export REPOSITORY=
# export TAG="""
    if out is not None:
        with open(out, "w") as f:
            f.write(env)
    print(env)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build docker images from target")

    parser.add_argument("out", nargs="?", help="Where to save the environment",)

    args = parser.parse_args()

    env_create(args.out)
