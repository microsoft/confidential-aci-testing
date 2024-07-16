#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import subprocess

from .vm_get_ids import vm_get_ids


def vm_remove(
    deployment_name: str,
    subscription: str,
    resource_group: str,
    **kwargs,
):
    for res_id in vm_get_ids(deployment_name, subscription, resource_group):
        res_name = res_id.split("/")[-1]
        subprocess.run(
            [
                "az",
                "resource",
                "delete",
                "--no-wait",
                "--subscription",
                subscription,
                "--resource-group",
                resource_group,
                "--resource-type",
                "Microsoft.ContainerInstance/containerGroups",
                "--name",
                res_name,
            ],
            check=True,
        )
        print(f"Removed resource: {res_name}")
