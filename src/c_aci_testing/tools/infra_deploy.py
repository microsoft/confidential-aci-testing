#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations

import os
import subprocess


def infra_deploy(
    subscription: str,
    resource_group: str,
    registry: str,
    managed_identity: str,
    location: str,
    github_repo: str,
    storage_account: str,
    **kwargs,
):
    bicep_template_dir = os.path.join(os.path.dirname(__file__), "..", "bicep")

    subprocess.run(["az", "account", "set", "--subscription", subscription])

    print("Checking if resource group exists")
    result = subprocess.run(
        ["az", "group", "exists", "--name", resource_group], capture_output=True, text=True, check=True
    )
    rg_exists = result.stdout.strip().lower() == "true"
    print(f"{resource_group} " + ("exists" if rg_exists else "does not exist"))

    if not rg_exists:
        print("Creating resource group and all resources")
        result = subprocess.run(
            [
                "az",
                "deployment",
                "sub",
                "create",
                "--location",
                location,
                "--template-file",
                os.path.join(bicep_template_dir, "resourceGroup.bicep"),
                "--parameters",
                f"name={resource_group}",
                "--parameters",
                f"registryName={registry}",
                "--parameters",
                f"managedIdentityName={managed_identity}",
                "--parameters",
                f"githubRepo={github_repo}",
                "--parameters",
                f"storageAccountName={storage_account}",
            ]
        )
        return

    # XXX: is this really necessary?

    print("Checking if container registry exists")
    result = subprocess.run(
        ["az", "acr", "show", "--name", registry, "--query", "name"], capture_output=True, text=True
    )
    deployed_name = result.stdout.rstrip(os.linesep).strip('"') + ".azurecr.io"
    registry_exists = result is not None and deployed_name == registry
    print(f"{registry} " + ("exists" if registry_exists else "does not exist"))

    if not registry_exists:
        print("Creating container registry")
        result = subprocess.run(
            [
                "az",
                "deployment",
                "group",
                "create",
                "--resource-group",
                resource_group,
                "--template-file",
                os.path.join(bicep_template_dir, "containerRegistry.bicep"),
                "--parameters",
                f"name={registry.split('.')[0]}",
                "--parameters",
                f"location={location}",
            ],
            check=True,
        )

    print(f"Checking if managed identity '{managed_identity}' exists")
    result = subprocess.run(
        ["az", "identity", "show", "--name", managed_identity, "--resource-group", resource_group, "--query", "name"],
        capture_output=True,
        text=True,
    )
    identity_exists = result is not None and result.stdout.replace('"', "").strip() == managed_identity
    print(f"{managed_identity} " + ("exists" if identity_exists else "does not exist"))

    if not identity_exists:
        print("Creating managed identity")
        result = subprocess.run(
            [
                "az",
                "deployment",
                "group",
                "create",
                "--resource-group",
                resource_group,
                "--template-file",
                os.path.join(bicep_template_dir, "managedIdentity.bicep"),
                "--parameters",
                f"name={managed_identity}",
                "--parameters",
                f"location={location}",
                "--parameters",
                f"githubRepo={github_repo}",
            ],
            check=True,
        )

    print(f"Checking if storage account '{storage_account}' exists")
    result = subprocess.run(
        [
            "az",
            "storage",
            "account",
            "show",
            "--name",
            storage_account,
            "--resource-group",
            resource_group,
            "--query",
            "name",
        ],
        capture_output=True,
        text=True,
    )
    account_exists = result is not None and result.stdout.replace('"', "").strip() == storage_account
    print(f"{storage_account} " + ("exists" if account_exists else "does not exist"))

    if not account_exists:
        print("Creating storage account")
        result = subprocess.run(
            [
                "az",
                "deployment",
                "group",
                "create",
                "--resource-group",
                resource_group,
                "--template-file",
                os.path.join(bicep_template_dir, "blobStorage.bicep"),
                "--parameters",
                f"name={storage_account}",
                "--parameters",
                f"location={location}",
                "--parameters",
                f"managedIdName={managed_identity}",
            ],
            check=True,
        )
