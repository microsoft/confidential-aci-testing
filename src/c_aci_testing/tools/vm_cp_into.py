#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import datetime

from ..utils.vm import upload_to_vm_and_run
from c_aci_testing.tools.vm_create import VM_CONTAINER_NAME


def vm_cp_into(
    src: str,
    dst: str,
    run_command: str,
    deployment_name: str,
    subscription: str,
    resource_group: str,
    storage_account: str,
    **kwargs,
):
    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

    commands = [run_command]
    if not run_command:
        commands = []

    upload_to_vm_and_run(
        src=src,
        dst=dst,
        vm_name=f"{deployment_name}-vm",
        subscription=subscription,
        resource_group=resource_group,
        storage_account=storage_account,
        container_name=VM_CONTAINER_NAME,
        blob_name=f"{deployment_name}vm_cp_into_{ts}",
        commands=commands,
    )
