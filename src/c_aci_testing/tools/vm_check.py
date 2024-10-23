#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

from c_aci_testing.utils.vm import run_on_vm


def vm_check(
    deployment_name: str,
    subscription: str,
    resource_group: str,
    prefix: str,
    **kwargs,
):
    check_output = run_on_vm(
        vm_name=f"{deployment_name}-vm",
        subscription=subscription,
        resource_group=resource_group,
        command=f"C:\\{prefix}\\check.ps1",
    )

    if "ERROR" in check_output:
        raise Exception("Check failed")
