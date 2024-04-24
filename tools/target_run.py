#!/usr/bin/env python3

# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import argparse
from contextlib import contextmanager
import os

from .images_pull import images_pull
from .images_build import images_build
from .images_push import images_push
from .policies_gen import policies_gen
from .aci_deploy import aci_deploy
from .aci_monitor import aci_monitor
from .aci_remove import aci_remove


@contextmanager
def target_run_ctx(
    target,
    name,
    registry=os.environ.get("REGISTRY"),
    subscription=os.environ.get("SUBSCRIPTION"),
    resource_group=os.environ.get("RESOURCE_GROUP"),
    managed_identity=os.environ.get("MANAGED_IDENTITY"),
    location=os.environ.get("LOCATION"),
    tag=os.environ.get("TAG"),
    parameters=None,
    follow=True,
    cleanup=True,
    repository=None,
    prefer_pull=False,
    gen_policies=True,
):
    services_to_build = None
    if prefer_pull:
        services_to_build = images_pull(
            target=target,
            registry=registry,
            repository=repository,
            tag=tag,
        )
    if not prefer_pull or services_to_build:
        images_build(
            target=target,
            registry=registry,
            repository=repository,
            tag=tag,
            services_to_build=services_to_build,
        )
        images_push(
            target=target,
            registry=registry,
            repository=repository,
            tag=tag,
        )
    if gen_policies:
        policies_gen(
            target=target,
            deployment_name=name,
            subscription=subscription,
            resource_group=resource_group,
            registry=registry,
            repository=repository,
            tag=tag,
        )
    ids = aci_deploy(
        target=target,
        subscription=subscription,
        resource_group=resource_group,
        name=name,
        location=location,
        managed_identity=managed_identity,
        tag=tag,
        parameters=parameters,
    )
    try:
        yield ids
        aci_monitor(
            subscription=subscription,
            resource_group=resource_group,
            name=None,
            ids=ids,
            follow=follow,
        )
    finally:
        if cleanup:
            aci_remove(
                subscription=subscription,
                resource_group=resource_group,
                name=None,
                ids=ids,
            )


def target_run(**kwargs):
    with target_run_ctx(**kwargs):
        ...


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate Security Policies for target"
    )

    parser.add_argument(
        "target",
        help="Target directory",
        default=os.environ.get("TARGET"),
        nargs="?",  # aka Optional
        type=lambda path: os.path.abspath(os.path.expanduser(path)),
    )

    # Image Information
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

    # Azure Information
    parser.add_argument(
        "--subscription",
        help="Azure Subscription ID",
        default=os.environ.get("SUBSCRIPTION"),
    )
    parser.add_argument(
        "--resource-group",
        "-g",
        help="Azure Resource Group ID",
        default=os.environ.get("RESOURCE_GROUP"),
    )

    # Deployment Info
    parser.add_argument("--name", "-n", help="Name of deployment", required=True)
    parser.add_argument(
        "--location", help="Location to deploy to", default=os.environ.get("LOCATION")
    )
    parser.add_argument(
        "--managed-identity",
        help="Managed Identiy",
        default=os.environ.get("MANAGED_IDENTITY"),
    )
    parser.add_argument("--parameters", help="Path to parameters file")
    parser.add_argument(
        "--no-cleanup", help="Path to parameters file", action="store_true"
    )
    parser.add_argument(
        "--no-follow", help="Path to parameters file", action="store_true"
    )
    parser.add_argument("--prefer-pull",
        help="Attempt to pull image and only build if that fails", action="store_true"
    )
    parser.add_argument("--skip-policy-gen",
        help="Skip policy generation, if policies are generated separately",
        action="store_true",
        default=os.environ.get("SKIP_POLICY_GEN") == "1",
    )

    args = parser.parse_args()

    target_run(
        target=args.target,
        subscription=args.subscription,
        resource_group=args.resource_group,
        registry=args.registry,
        repository=args.repository,
        tag=args.tag,
        name=args.name,
        location=args.location,
        managed_identity=args.managed_identity,
        parameters=args.parameters,
        follow=not args.no_follow,
        cleanup=not args.no_cleanup,
        prefer_pull=args.prefer_pull,
        gen_policies=not args.skip_policy_gen,
    )
