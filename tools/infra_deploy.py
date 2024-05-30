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

    print("Checking if resource group exists")
    result = subprocess.run(
        ["az", "group", "exists", "--name", resource_group],
        capture_output=True,
        text=True,
        check=True
    )
    rg_exists = result.stdout.strip().lower() == 'true'
    print(f"{resource_group} " + ("exists" if rg_exists else "does not exist"))

    if not rg_exists:
        print("Creating resource group and all resources")
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
        return

    print("Checking if container registry exists")
    result = subprocess.run(
        ["az", "acr", "show", "--name", registry, "--query", "name"],
        capture_output=True,
        text=True
    )
    deployed_name = result.stdout.rstrip(os.linesep).strip('"') + ".azurecr.io"
    registry_exists = result is not None and deployed_name == registry
    print(f"{registry} " + ("exists" if registry_exists else "does not exist"))

    if not registry_exists:
        print("Creating container registry")
        result = subprocess.run([
            "az", "deployment", "group", "create",
            "--resource-group", resource_group,
            "--template-file", os.path.join(os.path.dirname(__file__), "aci", "containerRegistry.bicep"),
            "--parameters", f"name={registry}",
            "--parameters", f"location={location}",
        ], check=True)

    print("Checking if managed identity exists")
    result = subprocess.run(["az", "identity", "show", "--name", managed_identity, "--resource-group", resource_group, "--query", "name"], capture_output=True, text=True)
    identity_exists = result is not None and result.stdout.strip('"') == managed_identity
    print(f"{managed_identity} " + ("exists" if identity_exists else "does not exist"))

    if not identity_exists:
        print("Creating managed identity")
        result = subprocess.run([
            "az", "deployment", "group", "create",
            "--resource-group", resource_group,
            "--template-file", os.path.join(os.path.dirname(__file__), "aci", "managedIdentity.bicep"),
            "--parameters", f"name={managed_identity}",
            "--parameters", f"location={location}",
            "--parameters", f"githubOrg={github_org}",
            "--parameters", f"githubRepo={github_repo}",
        ], check=True)


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
To run this successfully, you will need the following permissions in the account you log into the Azure CLI with:
- To deploy everything you need the owner role at the subscription level
- If the resource group already exists, you only need the owner role scoped to that resource group
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