#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import subprocess

from .aci_get_ids import aci_get_ids


def aci_monitor(
    deployment_name: str,
    subscription: str,
    resource_group: str,
    follow: bool = False,
    **kwargs,
):
    for id in aci_get_ids(deployment_name, subscription, resource_group):
        group_name = id.split("/")[-1]
        res = subprocess.run(
            [
                "az", "container", "show",
                "--subscription", subscription,
                "--resource-group", resource_group,
            ],
            stdout=subprocess.PIPE,
        )
        group_json = json.loads(res.stdout)
        for container_json in group_json["containers"]:
            print(f"Logs from {group_name} - {container_json["name"]}")
            subprocess.run([
                "az", "container", "logs",
                *(["--follow"] if follow else []),
                "--subscription", subscription,
                "--resource-group", resource_group,
                "--name", group_name,
                "--container-name", container_json["name"]
            ], check=not follow)
