#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import tempfile

from c_aci_testing.tools.vm_generate_scripts import make_configs
from c_aci_testing.tools.vm_create import VM_CONTAINER_NAME
from c_aci_testing.utils.vm import upload_to_vm_and_run, run_on_vm


def vm_runc(
    target_path: str,
    deployment_name: str,
    subscription: str,
    resource_group: str,
    storage_account: str,
    win_flavor: str,
    registry: str,
    repository: str,
    tag: str,
    prefix: str,
    **kwargs,
):
    lcow_config_blob_name = f"lcow_config_{deployment_name}"
    vm_name = f"{deployment_name}-vm"

    temp_dir = tempfile.mkdtemp()

    make_configs(
        target_path=target_path,
        subscription=subscription,
        resource_group=resource_group,
        deployment_name=deployment_name,
        win_flavor=win_flavor,
        registry=registry,
        repository=repository,
        tag=tag,
        prefix=prefix,
        output_conf_dir=temp_dir,
    )

    print(f"Uploading LCOW config and scripts to {vm_name}...")

    output = upload_to_vm_and_run(
        src=temp_dir,
        dst="C:\\" + prefix,
        subscription=subscription,
        resource_group=resource_group,
        vm_name=vm_name,
        storage_account=storage_account,
        container_name=VM_CONTAINER_NAME,
        blob_name=lcow_config_blob_name,
        commands=[f"cd C:\\{prefix}", ".\\run.ps1", 'Write-Output "run.ps1 result: $LASTEXITCODE"'],
    )

    if "ERROR" in output:
        raise Exception("Error detected in run output - container deployment failed")

    run_on_vm(
        vm_name=vm_name,
        subscription=subscription,
        resource_group=resource_group,
        command="C:/containerplat/crictl.exe pods; C:/containerplat/crictl.exe ps -a",
    )
