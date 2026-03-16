#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import os
import subprocess
import sys


def aci_get_ids(
    deployment_name: str,
    subscription: str,
    resource_group: str,
    **kwargs,
) -> list[str]:
    try:
        res = subprocess.run(
            [
                "az",
                "deployment",
                "group",
                "show",
                "--name",
                deployment_name,
                "--subscription",
                subscription,
                "--resource-group",
                resource_group,
                "--query",
                "properties.outputs.ids.value",
                "-o",
                "tsv",
            ],
            check=True,
            stdout=subprocess.PIPE,
        )
        ids = [id for id in res.stdout.decode().split(os.linesep) if id]
        return ids
    except subprocess.CalledProcessError:
        print(
            f"Failed to get deployment output for {deployment_name}. Attempting to find container group by name...",
            flush=True,
            file=sys.stderr,
        )

    try:
        container_res = subprocess.run(
            [
                "az",
                "container",
                "show",
                "--name",
                deployment_name,
                "--subscription",
                subscription,
                "--resource-group",
                resource_group,
                "--query",
                "id",
                "-o",
                "tsv",
            ],
            check=True,
            stdout=subprocess.PIPE,
        )
        container_id = container_res.stdout.decode().strip()
        if container_id:
            return [container_id]
    except subprocess.CalledProcessError:
        print(
            f"Failed to find container group {deployment_name} by name.",
            flush=True,
            file=sys.stderr,
        )

    return []
