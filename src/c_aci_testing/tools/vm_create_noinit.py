#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import uuid
import re

from c_aci_testing.tools.vm_get_ids import vm_get_ids

VM_CONTAINER_NAME = "container"


def vm_create_noinit(
    deployment_name: str,
    subscription: str,
    resource_group: str,
    location: str,
    managed_identity: str,
    use_official_images: bool,
    official_image_sku: str,
    official_image_version: str,
    vm_image: str,
    vm_size: str,
    vm_zone: str,
    **kwargs,
) -> list[str]:
    """
    :param cplat_feed: ADO feed name for containerplat, can be empty to use existing cache
    :param cplat_name: Name of the containerplat package, can be empty
    :param cplat_version: Version of the containerplat package, can be empty
    :param cplat_path: Path to an already downloaded containerplat package, can be empty
    :param cplat_blob_name: Name to use for the containerplat blob, can be empty for per-deployment blobs
    """

    if not vm_image and not use_official_images:
        raise ValueError("Either specify VM_IMAGE, or set USE_OFFICIAL_IMAGES to true")

    password = str(uuid.uuid4())
    password_file = os.path.join(tempfile.gettempdir(), f"{deployment_name}_password.txt")
    with open(password_file, "wt") as f:
        f.write(password)
    print(f"VM password written to {password_file}")

    hostname = re.sub(r"[^a-zA-Z0-9\-]", "", re.sub("_", "-", deployment_name))
    if not hostname or re.fullmatch(r"^[0-9]+$", hostname):
        hostname = "atlas-" + hostname
    if len(hostname) > 15:
        hostname = hostname[:15]

    parameters: dict = {
        "vmPassword": password,
        "location": location,
        "useOfficialImages": use_official_images,
        "officialImageSku": official_image_sku if official_image_sku else None,
        "officialImageVersion": official_image_version if official_image_version else None,
        "vmImage": vm_image if vm_image else None,
        "managedIDName": managed_identity,
        "vmSize": vm_size,
        "vmHostname": hostname,
    }

    if vm_zone:
        parameters["vmZones"] = [vm_zone]

    parameters_file = os.path.join(tempfile.gettempdir(), f"{deployment_name}_parameters.json")
    with open(parameters_file, "wt") as f:
        parameters_obj = {
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
            "contentVersion": "1.0.0.0",
            "parameters": {k: {"value": v} for k, v in parameters.items()},
        }
        json.dump(parameters_obj, f, indent=2)

    template_file = os.path.join(os.path.dirname(__file__), "..", "bicep", "containerplatVM.bicep")

    print(f"Deployment template: {template_file}")
    print(f"Deployment parameters file: {parameters_file}")

    print(f"{os.linesep}Deploying VM to Azure, view deployment here:")
    print(
        "%2F".join(
            [
                "https://ms.portal.azure.com/#blade/HubsExtension/DeploymentDetailsBlade/id/",
                "subscriptions",
                subscription,
                "resourceGroups",
                resource_group,
                "providers",
                "Microsoft.Resources",
                "deployments",
                deployment_name,
            ]
        )
    )
    print("")

    subprocess.run(
        [
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
            template_file,
            "--parameters",
            f"@{parameters_file}",
        ],
        check=True,
    )

    ids = vm_get_ids(
        deployment_name=deployment_name,
        subscription=subscription,
        resource_group=resource_group,
    )

    for id in ids:
        if id.endswith("-vm"):
            print("------------------------------------------------------------------------")
            print(f'Deployed {id.split("/")[-1]}, view here:')
            print(f"https://ms.portal.azure.com/#@microsoft.onmicrosoft.com/resource{id}")
            print("------------------------------------------------------------------------")

    return ids
