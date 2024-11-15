#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import os
import subprocess
import time

from c_aci_testing.utils.vm import (
    run_on_vm,
    download_single_file_from_vm,
    decode_utf8_or_utf16,
    upload_to_vm_and_run,
)
from c_aci_testing.tools.vm_cache_cplat import containerplat_cache
from c_aci_testing.tools.vm_create_noinit import vm_create_noinit

VM_CONTAINER_NAME = "container"


def check_vm_exists(
    subscription: str,
    resource_group: str,
    vm_name: str,
) -> bool:
    try:
        subprocess.run(
            [
                "az",
                "vm",
                "show",
                "--name",
                vm_name,
                "--subscription",
                subscription,
                "--resource-group",
                resource_group,
            ],
            check=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def vm_create(
    deployment_name: str,
    subscription: str,
    resource_group: str,
    location: str,
    managed_identity: str,
    use_official_images: bool,
    official_image_sku: str,
    official_image_version: str,
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

    vm_name = f"{deployment_name}-vm"
    vm_exists = check_vm_exists(
        subscription=subscription,
        resource_group=resource_group,
        vm_name=vm_name,
    )

    if not vm_exists:
        ids = vm_create_noinit(
            deployment_name=deployment_name,
            subscription=subscription,
            resource_group=resource_group,
            location=location,
            managed_identity=managed_identity,
            use_official_images=use_official_images,
            official_image_sku=official_image_sku,
            official_image_version=official_image_version,
            vm_image=vm_image,
            vm_size=vm_size,
            vm_zone=vm_zone,
        )
    else:
        ids = []
        print(f"{vm_name} already exists - skipping Azure deployment")

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
