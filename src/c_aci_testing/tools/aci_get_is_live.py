#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import json
import subprocess
from typing import List

from .aci_get_ids import aci_get_ids


def aci_get_is_live(
    deployment_name: str,
    subscription: str,
    resource_group: str,
    aci_ids: list[str] = [],
    **kwargs,
) -> bool:
    if aci_ids == []:
        aci_ids = aci_get_ids(deployment_name, subscription, resource_group)

    if aci_ids == []:
        return False

    for id in aci_ids:
        group_name = id.split("/")[-1]
        print(f"Checking {group_name}")

        result = subprocess.run([
            "az", "container", "show", "--ids", id,
            "--subscription", subscription,
            "--resource-group", resource_group,
        ], capture_output=True)

        if result.returncode != 0:
            return False
        try:
            container_state = json.loads(result.stdout.decode())
            if container_state["instanceView"]["state"] != "Running":
                return False
        except Exception:
            return False

    return True
