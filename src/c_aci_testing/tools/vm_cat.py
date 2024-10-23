#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import sys

from ..utils.vm import download_single_file_from_vm, decode_utf8_or_utf16


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
    sys.stdout.write(decode_utf8_or_utf16(raw_data))
