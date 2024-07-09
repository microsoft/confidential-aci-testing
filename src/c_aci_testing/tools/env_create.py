#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations


def env_create(
    **kwargs,
):
    print(
        """# Core Environment Variables
SUBSCRIPTION=
RESOURCE_GROUP=
REGISTRY=
MANAGED_IDENTITY=
LOCATION=
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
export GITHUB_REPO=$GITHUB_REPO
export REPOSITORY=$REPOSITORY
export TAG=$TAG"""
    )
