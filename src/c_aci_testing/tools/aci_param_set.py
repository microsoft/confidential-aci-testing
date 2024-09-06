#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations

import os
import re


def aci_param_set(
    target_path: str,
    parameters: list[str],
    add: bool = True,
    **kwargs,
):
    # Find the bicep param file
    for file in os.listdir(target_path):
        if file.endswith(".bicepparam"):
            biceparam_file_path = file

    # Load the param file
    with open(os.path.join(target_path, biceparam_file_path)) as f:
        biceparam_template = f.read()

    # Set parameters
    for parameter in parameters:
        key, *value = parameter.split("=")
        value = "=".join(value)
        print(f'Setting parameter {key} to {value[:50]}{"..." if len(value) > 50 else ""}')

        biceparam_template = re.sub(f"param {key}\s*=\s*'.*'", f"param {key}={value}", biceparam_template)
        biceparam_template = re.sub(
            f"param {key}\s*=\s*\\{{.*\\}}",
            f"param {key}={value}",
            biceparam_template,
            flags=re.DOTALL,
        )
        biceparam_template = re.sub(rf"param {key}\s*=\s*\[.*\]", f"param {key}={value}", biceparam_template)
        if f"param {key}=" not in biceparam_template and add:
            biceparam_template += f"{os.linesep}param {key}={value}"

    # Save the new file
    with open(os.path.join(target_path, biceparam_file_path), "w") as f:
        f.write(biceparam_template)
