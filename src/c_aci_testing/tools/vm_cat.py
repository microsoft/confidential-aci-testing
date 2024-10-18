#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import sys

from ..utils.vm import download_single_file_from_vm


def vm_cat(
    file_path: str,
    deployment_name: str,
    subscription: str,
    resource_group: str,
    managed_identity: str,
    **kwargs,
):
    vm_name = f"{deployment_name}-vm"
    raw_data = download_single_file_from_vm(
        vm_name=vm_name,
        subscription=subscription,
        resource_group=resource_group,
        managed_identity=managed_identity,
        file_path=file_path,
    )

    try:
        str_data = raw_data.decode("utf-8")
        sys.stdout.write(str_data)
    except UnicodeDecodeError:
        try:
            str_data = raw_data.decode("utf-16")
            sys.stdout.write(str_data)
        except UnicodeDecodeError:
            sys.stdout.buffer.write(raw_data)
