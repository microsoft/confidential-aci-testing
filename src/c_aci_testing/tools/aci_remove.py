#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import subprocess

from .aci_get_ids import aci_get_ids


def aci_remove(
    deployment_name: str,
    subscription: str,
    resource_group: str,
    **kwargs,
):
    resources = aci_get_ids(deployment_name, subscription, resource_group)

    if not resources:
        print(
            f"Failed to get deployment output. Removing any container group of the same name as the deployment: {deployment_name}"
        )
        resources = [
            f"/subscriptions/{subscription}/resourceGroups/{resource_group}/providers/Microsoft.ContainerInstance/containerGroups/{deployment_name}"
        ]

    for id in resources:
        group_name = id.split("/")[-1]
        # az resource delete will return successfully even if the resource does
        # not exist.
        subprocess.run([
            "az", "resource", "delete", "--no-wait",
            "--subscription", subscription,
            "--resource-group", resource_group,
            "--resource-type", "Microsoft.ContainerInstance/containerGroups",
            "--name", group_name,
        ], check=True)
        print(f"Removed container group: {group_name}")
