#!/usr/bin/env python3

# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import argparse
import json
import os
import subprocess

from .aci_param_set import aci_param_set
from .target_find_files import find_bicep_file, find_bicep_param_file


def aci_deploy(
    target,
    subscription,
    resource_group,
    name,
    location,
    tag,
    managed_identity,
    parameters,
):

    assert target, "Target is required"
    assert resource_group, "Resource Group is required"

    print("Updating parameter file with deployment info")
    param_file_path = os.path.join(target, find_bicep_param_file(target))
    with open(param_file_path, "r") as file:
        content = file.read().split(os.linesep)

    if location and any(line.startswith("param location") for line in content):
        aci_param_set(param_file_path, "location", f"'{location}'")
    if managed_identity and any(line.startswith("param managedIDName") for line in content):
        aci_param_set(param_file_path, "managedIDName", f"'{managed_identity}'")
    if tag and any(line.startswith("param tag") for line in content):
        aci_param_set(param_file_path, "tag", f"'{tag}'")

    az_command = [
        "az", "deployment", "group", "create",
        "-n", name,
        *(["--subscription", subscription] if subscription else []),
        "--resource-group", resource_group,
        "--template-file", os.path.join(target, find_bicep_file(target)),
        "--parameters", param_file_path,
        "--query", "properties.outputs.ids.value",
        "-o", "tsv",
    ]
    for parameter in parameters or []:
        key = parameter.split("=")[0]
        value = "=".join(parameter.split("=")[1:]).strip('"')
        az_command.extend(["--parameters", f"{key}={value}"])

    if not subscription:
        output = subprocess.check_output(["az", "account", "show"])
        subscription = json.loads(output)["id"]

    print(f"{os.linesep}Deploying to Azure, view deployment here:")
    print("%2F".join([
        "https://ms.portal.azure.com/#blade/HubsExtension/DeploymentDetailsBlade/id/",
        "subscriptions", subscription,
        "resourceGroups", resource_group,
        "providers", "Microsoft.Resources", "deployments", name,
    ]))
    print("")

    subprocess.run(az_command, check=True)

    res = subprocess.run(
        [
            "az", "deployment", "group", "show",
            "--name", name,
            *(["--subscription", subscription] if subscription else []),
            "--resource-group", resource_group,
            "--query", "properties.outputs.ids.value",
            "-o", "tsv",
        ],
        check=True,
        stdout=subprocess.PIPE,
    )
    ids = [id for id in res.stdout.decode().split(os.linesep) if id]
    for id in ids:
        print(f'Deployed {os.linesep}{id.split("/")[-1]}, view here:')
        print(f"https://ms.portal.azure.com/#@microsoft.onmicrosoft.com/resource/{id}")
    return ids

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy ACI for target")

    parser.add_argument(
        "target",
        help="Target directory",
        default=os.environ.get("TARGET"),
        nargs="?",  # aka Optional
        type=lambda path: os.path.abspath(os.path.expanduser(path)),
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
    parser.add_argument(
        "--tag", help="Image Tag", default=os.environ.get("TAG") or "latest"
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
    parser.add_argument("--parameters", help="Path to parameters file", action="append")

    args = parser.parse_args()

    aci_deploy(
        target=args.target,
        subscription=args.subscription,
        resource_group=args.resource_group,
        name=args.name,
        location=args.location,
        managed_identity=args.managed_identity,
        parameters=args.parameters,
        tag=args.tag,
    )
