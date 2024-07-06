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
    for id in aci_get_ids(deployment_name, subscription, resource_group):
        group_name = id.split("/")[-1]
        subprocess.run([
            "az", "resource", "delete", "--no-wait",
            "--subscription", subscription,
            "--resource-group", resource_group,
            "--resource-type", "Microsoft.ContainerInstance/containerGroups",
            "--name", group_name,
        ], check=True)
        print(f"Removed container group: {group_name}")
