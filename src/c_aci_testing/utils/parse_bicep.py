#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations

import json
import os
import subprocess
from typing import Iterable, Tuple

from c_aci_testing.tools.aci_param_set import aci_param_set


def parse_bicep(
    target_path: str,
    subscription: str,
    resource_group: str,
    deployment_name: str,
    registry: str,
    repository: str,
    tag: str,
) -> Iterable[Tuple[str, dict, Iterable[dict]]]:

    bicep_file_path = None
    bicepparam_file_path = None

    # Find the bicep files
    for file in os.listdir(target_path):
        if file.endswith(".bicep"):
            bicep_file_path = os.path.join(target_path, file)
        elif file.endswith(".bicepparam"):
            bicepparam_file_path = os.path.join(target_path, file)

    if not bicep_file_path:
        raise FileNotFoundError(f"No bicep file found in {target_path}")
    if not bicepparam_file_path:
        raise FileNotFoundError(f"No bicepparam file found in {target_path}")

    # Set required parameters in bicep param file
    aci_param_set(
        target_path,
        parameters=[
            f"{k}='{v}'"
            for k, v in {
                "registry": registry,
                "repository": repository or "",
                "tag": tag or "",
            }.items()
        ],
        add=False,  # If the user removed a field, don't re-add it
    )

    # Create an ARM template with parameters resolved
    print("Resolving parameters using what-if deployment")
    res = subprocess.run(
        [
            "az",
            "deployment",
            "group",
            "what-if",
            "--name",
            deployment_name,
            "--no-pretty-print",
            "--mode",
            "Complete",
            "--subscription",
            subscription,
            "--resource-group",
            resource_group,
            "--template-file",
            bicep_file_path,
            "--parameters",
            bicepparam_file_path,
        ],
        check=True,
        stdout=subprocess.PIPE,
    )

    resolves_json = json.loads(res.stdout)
    for change in resolves_json["changes"]:
        result = change.get("after")
        if result:
            for prefix in (
                "providers/Microsoft.ContainerInstance/containerGroups/",
                "providers/Microsoft.ContainerInstance/containerGroupProfiles/",
            ):
                container_group_id = (
                    result["id"]
                    .split(prefix)[-1]
                    .replace(deployment_name, bicep_file_path.split("/")[-1].split(".")[0])
                    .replace("-", "_")
                )

                if prefix in result["id"]:

                    def get_containers(group):
                        if "containers" in group["properties"]:
                            for container in group["properties"]["containers"]:
                                yield container

                    yield container_group_id, result, get_containers(result)
