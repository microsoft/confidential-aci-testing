#!/usr/bin/env python3

# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import argparse
import json
import os
import subprocess


def aci_is_live(
    subscription,
    resource_group,
    name,
):
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
        res = subprocess.run([
            "az", "container", "show", "--ids", id,
        ], stdout=subprocess.PIPE)
        container_state = json.loads(res.stdout.decode())
        if container_state["instanceView"]["state"] != "Running":
            return None

    return ids

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy ACI for target")

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

    args = parser.parse_args()

    ids = aci_is_live(
        subscription=args.subscription,
        resource_group=args.resource_group,
        name=args.name,
    )

    if ids:
        print(f"Deployment resources are live: {ids}")
