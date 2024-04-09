#!/usr/bin/env python3

# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import argparse
import os
import subprocess

def infra_deploy(subscription, resource_group, registry, managed_identity, location, github_org, github_repo):

    assert subscription is not None, "Subscription must be set"
    assert resource_group is not None, "Resource Group must be set"
    assert registry is not None, "Registry must be set"
    assert managed_identity is not None, "Managed Identity must be set"
    assert location is not None, "Location must be set"

    subprocess.run(["az", "account", "set", "--subscription", subscription])

    result = subprocess.run([
        "az", "deployment", "sub", "create",
        "--location", location,
        "--template-file", os.path.join(os.path.dirname(__file__), "aci", "resourceGroup.bicep"),
        "--parameters", f"name={resource_group}",
        "--parameters", f"registryName={registry}",
        "--parameters", f"managedIdentityName={managed_identity}",
        "--parameters", f"githubOrg={github_org}",
        "--parameters", f"githubRepo={github_repo}",
    ])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy required infrastructure to run targets")

    parser.add_argument("--subscription",
        help="Azure Subscription ID", default=os.environ.get("SUBSCRIPTION"))
    parser.add_argument("--resource-group", '-g',
        help="Azure Resource Group ID", default=os.environ.get("RESOURCE_GROUP"))
    parser.add_argument("--registry",
        help="Container Registry", default=os.environ.get("REGISTRY"))
    parser.add_argument("--managed-identity",
        help="Managed Identiy", default=os.environ.get("MANAGED_IDENTITY"))
    parser.add_argument("--location",
        help="Location to deploy to", default=os.environ.get("LOCATION"))
    parser.add_argument("--github-org",
        help="Github Organisation to link credential", default=os.environ.get("GITHUB_ORG"))
    parser.add_argument("--github-repo",
        help="Github Repository to link credential", default=os.environ.get("GITHUB_REPO"))

    args = parser.parse_args()

    print("""
This currently fails if you don't have the Owner role at the subscription level
You can still manually deploy aci/resourceGroup.bicep with the bicep VS Code extension
    """)

    infra_deploy(
        subscription=args.subscription,
        resource_group=args.resource_group,
        registry=args.registry,
        managed_identity=args.managed_identity,
        location=args.location,
        github_org=args.github_org,
        github_repo=args.github_repo,
    )