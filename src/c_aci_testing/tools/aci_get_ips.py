#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import subprocess

from .aci_get_ids import aci_get_ids


def aci_get_ips(
    deployment_name: str,
    subscription: str,
    resource_group: str,
    **kwargs,
) -> list[str]:
    ip_addresses = []

    for id in aci_get_ids(deployment_name, subscription, resource_group):
        result = subprocess.run([
            "az", "container", "show",
            "--query", "ipAddress.ip",
            "--output", "tsv",
            "--subscription", subscription,
            "--resource-group", resource_group,
            "--ids", id,
        ], capture_output=True, text=True, check=True)
        ip_addresses.append(result.stdout.rstrip("\n"))

    return ip_addresses
