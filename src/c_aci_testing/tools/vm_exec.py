#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

from ..utils.vm import run_on_vm


def vm_exec(
    cmd: str,
    deployment_name: str,
    subscription: str,
    resource_group: str,
    **kwargs,
):
    vm_name = f"{deployment_name}-vm"
    run_on_vm(
        vm_name=vm_name,
        subscription=subscription,
        resource_group=resource_group,
        command=cmd,
    )
