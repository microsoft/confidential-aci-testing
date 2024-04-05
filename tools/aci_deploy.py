#!/usr/bin/env python3

import argparse
import os
import subprocess
from aci_param_set import update_param

def aci_deploy(target, subscription, resource_group, name, location, managed_identity, parameters):

    assert target is not None, "Target is required"

    param_file_path = os.path.join(target, ".bicepparam")
    if location is not None:
        update_param(param_file_path, "location", location)
    if managed_identity is not None:
        update_param(param_file_path, "managedIDName", managed_identity)

    az_command = [
        "az", "deployment", "group", "create",
        "-n", name,
        *(["--subscription", subscription] if subscription else []),
        *(["--resource-group", resource_group] if resource_group else []),
        "--template-file", os.path.join(target, ".bicep"),
        "--parameters", param_file_path,
        "--query", "properties.outputs.id.value", "-o", "tsv",
    ]
    for parameter in parameters or []:
        key = parameter.split("=")[0]
        value = "=".join(parameter.split("=")[1:]).strip("\"")
        az_command.extend(["--parameters", f'{key}={value}'])

    result = subprocess.run(az_command, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr)
        return

    print(result.stdout)
    return result.stdout


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy ACI for target")

    parser.add_argument("target",
        help="Target directory", default=os.environ.get("TARGET"),
        nargs="?", # aka Optional
        type=lambda path: os.path.abspath(os.path.expanduser(path)))

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
    )