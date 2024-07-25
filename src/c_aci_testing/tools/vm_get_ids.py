#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import os
import subprocess


def vm_get_ids(
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
    except subprocess.CalledProcessError:
        return []

    ids = [id for id in res.stdout.decode().split(os.linesep) if id]
    return ids
