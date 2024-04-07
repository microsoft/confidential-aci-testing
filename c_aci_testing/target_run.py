#!/usr/bin/env python3

import argparse
import os
from .images_build import images_build
from .images_push import images_push
from .policies_gen import policies_gen
from .aci_deploy import aci_deploy
from .aci_monitor import aci_monitor
from .aci_remove import aci_remove

def target_run(target, registry, repository, tag, subscription, resource_group, name, location, managed_identity, parameters, cleanup):

    images_build(
        target=target,
        registry=registry,
        repository=repository,
        tag=tag,
    )
    images_push(
        target=target,
        registry=registry,
        repository=repository,
        tag=tag,
    )
    policies_gen(
        target=target,
        registry=registry,
        repository=repository,
        tag=tag,
    )
    print("Deploying Container to Azure")
    id = aci_deploy(
        target=target,
        subscription=subscription,
        resource_group=resource_group,
        name=name,
        location=location,
        managed_identity=managed_identity,
        parameters=parameters,
    ).rstrip("\n")
    print("Deployment complete, monitoring...")
    try:
        aci_monitor(
            subscription=subscription,
            resource_group=resource_group,
            name=None,
            ids=id
        )
    finally:
        if cleanup:
            print("Removing container")
            aci_remove(
                subscription=subscription,
                resource_group=resource_group,
                name=None,
                ids=id
            )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Security Policies for target")

    parser.add_argument("target",
        help="Target directory", default=os.environ.get("TARGET"),
        nargs="?", # aka Optional
        type=lambda path: os.path.abspath(os.path.expanduser(path)))

    # Image Information
    parser.add_argument("--registry",
        help="Container Registry", default=os.environ.get("REGISTRY"))
    parser.add_argument("--repository",
        help="Container Repository", default=os.environ.get("REPOSITORY"))
    parser.add_argument("--tag",
        help="Image Tag", default=os.environ.get("TAG") or "latest")

    # Azure Information
    parser.add_argument("--subscription",
        help="Azure Subscription ID", default=os.environ.get("SUBSCRIPTION"))
    parser.add_argument("--resource-group", '-g',
        help="Azure Resource Group ID", default=os.environ.get("RESOURCE_GROUP"))

    # Deployment Info
    parser.add_argument("--name", "-n", help="Name of deployment", required=True)
    parser.add_argument("--location", 
        help="Location to deploy to", default=os.environ.get("LOCATION"))
    parser.add_argument("--managed-identity",
        help="Managed Identiy", default=os.environ.get("MANAGED_IDENTITY"))
    parser.add_argument("--parameters", help="Path to parameters file")
    parser.add_argument("--no-cleanup", help="Path to parameters file", action="store_true")
    
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
        cleanup=not args.no_cleanup,
    )
