#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations

import os


def get_target_name(
    target_path: str,
) -> str:
    for file in os.listdir(target_path):
        if file.endswith(".bicep"):
            return file.replace(".bicep", "")
