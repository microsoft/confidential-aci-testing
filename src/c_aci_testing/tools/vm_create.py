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
import time
import re

from c_aci_testing.tools.vm_get_ids import vm_get_ids
from c_aci_testing.utils.vm import (
    run_on_vm,
    download_single_file_from_vm,
    decode_utf8_or_utf16,
    upload_to_vm_and_run,
)
from c_aci_testing.tools.vm_cache_cplat import containerplat_cache

VM_CONTAINER_NAME = "container"


def vm_create(
    deployment_name: str,
    subscription: str,
    resource_group: str,
    location: str,
    managed_identity: str,
    vm_image: str,
    cplat_feed: str,
    cplat_name: str,
    cplat_version: str,
    cplat_blob_name: str,
    cplat_path: str,
    storage_account: str,
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
    if not cplat_blob_name:
        cplat_blob_name = f"containerplat_{deployment_name}"

    if cplat_path or cplat_feed or cplat_name or cplat_version or not cplat_blob_name:
        containerplat_cache(
            cplat_blob_name=cplat_blob_name,
            storage_account=storage_account,
            container_name=VM_CONTAINER_NAME,
            cplat_feed=cplat_feed,
            cplat_name=cplat_name,
            cplat_version=cplat_version,
            cplat_path=cplat_path,
        )

    cplat_blob_url = f"https://{storage_account}.blob.core.windows.net/{VM_CONTAINER_NAME}/{cplat_blob_name}"

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
        "vmImage": vm_image,
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

    vm_name = f"{deployment_name}-vm"

    print("Downloading containerplat on VM")
    run_on_vm(
        vm_name=vm_name,
        subscription=subscription,
        resource_group=resource_group,
        command="\r\n".join(
            [
                f'C:\\storage_get.ps1 -Uri "{cplat_blob_url}" -OutFile "C:\\containerplat.tar" 2>&1 >> C:\\bootstrap.log',
                "tar -xf C:\\containerplat.tar -C C:\\ 2>&1 >> C:\\bootstrap.log",
                'echo "result: $LASTEXITCODE"',
            ]
        ),
    )

    print("Bootstrapping VM")
    upload_to_vm_and_run(
        src=os.path.join(os.path.dirname(__file__), "..", "templates", "l1_initialize.ps1"),
        dst="C:\\l1_initialize.ps1",
        subscription=subscription,
        resource_group=resource_group,
        vm_name=vm_name,
        storage_account=storage_account,
        container_name=VM_CONTAINER_NAME,
        blob_name=f"{deployment_name}_l1_initialize.ps1",
        commands=[
            "C:\\l1_initialize.ps1",
        ],
    )

    tries = 0
    while True:
        tries += 1

        try:
            raw_output = download_single_file_from_vm(
                vm_name=vm_name,
                subscription=subscription,
                resource_group=resource_group,
                storage_account=storage_account,
                container_name=VM_CONTAINER_NAME,
                file_path="C:\\bootstrap.log",
            )
        except Exception as e:
            print(f"Failed to download bootstrap.log: {e}")
            if tries < 12:
                print("Retrying...")
                time.sleep(20)
                continue
            raise

        output = decode_utf8_or_utf16(raw_output)
        if "DEPLOY-SUCCESS" in output:
            print(output)
            break
        if "DEPLOY-ERROR" in output:
            print(output)
            raise Exception("Bootstrap error detected")
        if tries < 12:
            print("Waiting for VM to finish bootstrapping...")
            print("Current output:")
            print(output)
            time.sleep(20)
            continue
        print(output)
        raise Exception("VM did not finish bootstrapping in time")

    output = run_on_vm(
        vm_name=vm_name,
        subscription=subscription,
        resource_group=resource_group,
        command="C:/ContainerPlat/crictl.exe version; C:/ContainerPlat/crictl.exe ps",
    )
    if "containerd" not in output:
        raise Exception("ContainerPlat check failed")

    return ids
