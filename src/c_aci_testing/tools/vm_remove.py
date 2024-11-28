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
    remaining_resources = set(vm_get_ids(deployment_name, subscription, resource_group))

    while remaining_resources:
        print(f"Deleting {len(remaining_resources)} resources...")

        res = subprocess.run(
            [
                "az",
                "resource",
                "delete",
                "--subscription",
                subscription,
                "--resource-group",
                resource_group,
                "--ids",
                *remaining_resources,
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if res.returncode != 0:
            print(f"Failed to delete resources: {res.stderr.decode()}")
            break

        deleted_resources = set()
        for res_id in remaining_resources:
            res_name = res_id.split("/")[-1]
            res = subprocess.run(
                [
                    "az",
                    "resource",
                    "show",
                    "--ids",
                    res_id,
                ],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            if res.returncode != 0:
                deleted_resources.add(res_id)
                print(f"Removed resource: {res_name}")

        remaining_resources -= deleted_resources
