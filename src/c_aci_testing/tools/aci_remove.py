#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import subprocess
import time

from .aci_get_ids import aci_get_ids


def aci_remove(
    deployment_name: str,
    subscription: str,
    resource_group: str,
    **kwargs,
):
    resources = aci_get_ids(deployment_name, subscription, resource_group)

    for id in resources:
        group_name = id.split("/")[-1]
        # az resource delete will return successfully even if the resource does
        # not exist.

        cmd = [
            "az", "resource", "delete",
            "--no-wait",
            "--subscription", subscription,
            "--resource-group", resource_group,
            "--resource-type", "Microsoft.ContainerInstance/containerGroups",
            "--name", group_name,
        ]

        for attempt in range(5):
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"Removed container group: {group_name}")
                break

            err = (result.stderr or result.stdout or "").lower()
            if "already deleting" in err or "being deleted" in err:
                print(f"Delete underway container group: {group_name}")
                break
            
            if "not found" in err:
                print(f"Not found when deleing container group: {group_name}")
                break

            time.sleep(10)
        else:
            print(f"Failed to removed container group: {group_name}")
