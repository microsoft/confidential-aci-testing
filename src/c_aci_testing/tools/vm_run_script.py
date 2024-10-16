#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

from os import path

from ..utils.vm import upload_to_vm_and_run


def vm_run_script(
    target_path: str,
    script_file: str,
    deployment_name: str,
    subscription: str,
    resource_group: str,
    managed_identity: str,
    **kwargs,
):
    storage_account = "cacitestingstorage"

    if "/" in script_file or "\\" in script_file:
        raise ValueError("script_file must be a file name within target_path, not a path")

    upload_to_vm_and_run(
        target_path=target_path,
        vm_path="C:\\" + path.split(target_path)[-1],
        vm_name=f"{deployment_name}-vm",
        subscription=subscription,
        resource_group=resource_group,
        storage_account=storage_account,
        container_name="container",
        blob_name=f"{deployment_name}_vm_run_script_{path.dirname(target_path)}",
        managed_identity=managed_identity,
        run_script=script_file,
    )
