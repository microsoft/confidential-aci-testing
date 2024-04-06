#!/usr/bin/env python3


def env_create():
    print(
"""# Core Environment Variables
SUBSCRIPTION=""
RESOURCE_GROUP=""
REGISTRY=""
MANAGED_IDENTITY=""
LOCATION=""

# Per Target Options that can also be set at runtime
# REPOSITORY=""
# TAG="""""
)

if __name__ == "__main__":
    env_create()
