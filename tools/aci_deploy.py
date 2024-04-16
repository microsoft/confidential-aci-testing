#!/usr/bin/env python3

# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import argparse
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

    assert target is not None, "Target is required"
    assert resource_group is not None, "Resource Group is required"

    param_file_path = os.path.join(target, find_bicep_param_file(target))
    if location is not None:
        aci_param_set(param_file_path, "location", location)
    if managed_identity is not None:
        aci_param_set(param_file_path, "managedIDName", managed_identity)
    if tag is not None:
        aci_param_set(param_file_path, "tag", tag)

    az_command = [
        "az",
        "deployment",
        "group",
        "create",
        "-n",
        name,
        *(["--subscription", subscription] if subscription else []),
        "--resource-group",
        resource_group,
        "--template-file",
        os.path.join(target, find_bicep_file(target)),
        "--parameters",
        param_file_path,
        "--query",
        "properties.outputs.id.value",
        "-o",
        "tsv",
    ]
    for parameter in parameters or []:
        key = parameter.split("=")[0]
        value = "=".join(parameter.split("=")[1:]).strip('"')
        az_command.extend(["--parameters", f"{key}={value}"])

    subprocess.run(az_command, check=True)

    return subprocess.run(
        [
            "az",
            "deployment",
            "group",
            "show",
            "--name",
            name,
            *(["--subscription", subscription] if subscription else []),
            "--resource-group",
            resource_group,
            "--query",
            "properties.outputs.id.value",
            "-o",
            "tsv",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.rstrip("\n")


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
