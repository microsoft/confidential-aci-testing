#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

from c_aci_testing.tools.vm_create import VM_CONTAINER_NAME
from ..utils.vm import download_single_file_from_vm


def vm_cp_out(
    file_path: str,
    deployment_name: str,
    subscription: str,
    resource_group: str,
    storage_account: str,
    out_file: str,
    **kwargs,
):
    vm_name = f"{deployment_name}-vm"
    download_single_file_from_vm(
        vm_name=vm_name,
        subscription=subscription,
        resource_group=resource_group,
        file_path=file_path,
        storage_account=storage_account,
        container_name=VM_CONTAINER_NAME,
        binary=True,
        out_file=out_file,
    )
