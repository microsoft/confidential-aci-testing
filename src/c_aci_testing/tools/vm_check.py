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
    lcow_dir_name: str,
    **kwargs,
):
    check_output = run_on_vm(
        vm_name=f"{deployment_name}-vm",
        resource_group=resource_group,
        command=f"try {{ cd C:\\{lcow_dir_name}; .\\check.ps1 }} catch {{ Write-Output 'ERROR: failed to run check' $_.Exception.ToString() }}",
    )

    if "ERROR" in check_output:
        raise Exception("Check failed")
