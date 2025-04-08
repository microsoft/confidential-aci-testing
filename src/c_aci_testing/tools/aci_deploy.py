#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import json

from .aci_get_ids import aci_get_ids
from .aci_param_set import aci_param_set

from c_aci_testing.utils.parse_bicep import bicep_build


def aci_deploy(
    target_path: str,
    deployment_name: str,
    subscription: str,
    resource_group: str,
    location: str,
    managed_identity: str,
    **kwargs,
) -> list[str]:
    # Set required parameters in bicep param file
    aci_param_set(
        target_path,
        parameters=[f"{k}='{v}'" for k, v in {
            "location": location,
            "managedIDName": managed_identity,
        }.items()],
        add=False,
    )

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

    template_json, parameters_json = bicep_build(target_path)
    temp_arm_path = tempfile.mktemp(suffix=".json")
    temp_param_path = tempfile.mktemp(suffix=".json")
    with open(temp_arm_path, "wt") as temp_arm_file:
        json.dump(template_json, temp_arm_file, indent=2)
    with open(temp_param_path, "wt") as temp_param_file:
        json.dump(parameters_json, temp_param_file, indent=2)

    az_command = [
        "az",
        "deployment",
        "group",
        "create",
        "-n",
        deployment_name,
        "--subscription",
        subscription,
        "--resource-group",
        resource_group,
        "--template-file",
        temp_arm_path,
        "--parameters",
        f"@{temp_param_path}",
        "--query",
        "properties.outputs.ids.value",
        "-o",
        "tsv",
    ]

    print(f"ARM template saved to: {temp_arm_path}")
    print(f"Parameters saved to: {temp_param_path}")

    print(f"{os.linesep}Deploying to Azure, view deployment here:")
    print("%2F".join([
        "https://ms.portal.azure.com/#blade/HubsExtension/DeploymentDetailsBlade/id/",
        "subscriptions", subscription,
        "resourceGroups", resource_group,
        "providers", "Microsoft.Resources", "deployments", deployment_name,
    ]))
    print("")

    print(f"Running: {' '.join(az_command)}")

    sys.stdout.flush()
    sys.stderr.flush()

    res = subprocess.run(az_command)
    if res.returncode != 0:
        raise RuntimeError(f"Deployment failed with return code {res.returncode}")

    ids = aci_get_ids(
        deployment_name=deployment_name,
        subscription=subscription,
        resource_group=resource_group,
    )

    for id in ids:
        print(f'Deployed {os.linesep}{id.split("/")[-1]}, view here:')
        print(f"https://ms.portal.azure.com/#@microsoft.onmicrosoft.com/resource{id}")

    os.remove(temp_arm_path)

    return ids
