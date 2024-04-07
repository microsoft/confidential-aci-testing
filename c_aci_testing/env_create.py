#!/usr/bin/env python3

import argparse


def env_create(out=None):
    env = \
"""# Core Environment Variables
SUBSCRIPTION=
RESOURCE_GROUP=
REGISTRY=
MANAGED_IDENTITY=
LOCATION=

# Per Target Options that can also be set at runtime
# REPOSITORY=
# TAG="""
    if out is not None:
        with open(out, "w") as f:
            f.write(env)
    print(env)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build docker images from target")

    parser.add_argument("out", nargs="?", help="Where to save the environment",)

    args = parser.parse_args()

    env_create(args.out)
