#!/usr/bin/env python3

# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import argparse


def env_create(out=None):
    env = \
"""# Core Environment Variables
SUBSCRIPTION=
RESOURCE_GROUP=
REGISTRY=
MANAGED_IDENTITY=
LOCATION=
GITHUB_ORG=
GITHUB_REPO=

# Per Target Options that can also be set at runtime
# REPOSITORY=
# TAG=

# Support source-ing the env file as well as providing it directly
export SUBSCRIPTION=$SUBSCRIPTION
export RESOURCE_GROUP=$RESOURCE_GROUP
export REGISTRY=$REGISTRY
export MANAGED_IDENTITY=$MANAGED_IDENTITY
export LOCATION=$LOCATION
export GITHUB_ORG=$GITHUB_ORG
export GITHUB_REPO=$GITHUB_REPO
export REPOSITORY=$REPOSITORY
export TAG=$TAG"""
    if out is not None:
        with open(out, "w") as f:
            f.write(env)
    print(env)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build docker images from target")

    parser.add_argument("out", nargs="?", help="Where to save the environment",)

    args = parser.parse_args()

    env_create(args.out)
