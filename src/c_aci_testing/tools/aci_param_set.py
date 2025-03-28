#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations

import os
import re

from c_aci_testing.utils.find_bicep import find_bicep_files


def aci_param_set(
    target_path: str,
    parameters: list[str],
    add: bool = True,
    **kwargs,
):
    _, bicepparam_file_path = find_bicep_files(target_path)

    # Load the param file
    with open(os.path.join(target_path, bicepparam_file_path), encoding="utf-8") as f:
        biceparam_content = f.read()

    # Set parameters
    for parameter in parameters:
        if "=" not in parameter:
            raise ValueError(f"Parameter '{parameter}' is not in 'key=value' format.")

        key, value = parameter.split("=", 1)
        key = key.strip()
        value = value.strip()
        escaped_key = re.escape(key)
        print(f"Setting parameter '{key}' to {value[:50]}{'...' if len(value) > 50 else ''}")

        # Prepare regex patterns with parameter types
        patterns = [
            # (pattern, param_type)
            (rf"(param\s+{escaped_key}\s*=\s*)('.*?')", "string"),
            (rf"(param\s+{escaped_key}\s*=\s*)({{.*?}})", "object"),
            (rf"(param\s+{escaped_key}\s*=\s*)(\[.*?\])", "array"),
            (rf"(param\s+{escaped_key}\s*=\s*)([-+]?\d+)", "int"),
            (rf"(param\s+{escaped_key}\s*=\s*)(true|false)", "bool"),
        ]

        # Flag to check if parameter was found and replaced
        param_found = False

        for pattern, param_type in patterns:

            def replace_func(match):
                nonlocal param_found
                param_found = True
                if param_type == "string":
                    # Ensure the value is enclosed in single quotes
                    val = value.strip("'\"")
                    return f"{match.group(1)}'{val}'"
                else:
                    # For other types, use the value as-is
                    return f"{match.group(1)}{value}"

            biceparam_content, num_subs = re.subn(pattern, replace_func, biceparam_content, flags=re.DOTALL)
            if param_found:
                break  # Stop if we've found and replaced the parameter

        # Add new parameter if not found
        if not param_found and add:
            # Determine parameter type based on value
            if value.lower() in ["true", "false"]:
                param_line = f"param {key}={value.lower()}"
            elif re.match(r"^[-+]?\d+$", value):
                param_line = f"param {key}={value}"
            elif value.startswith("{") and value.endswith("}"):
                param_line = f"param {key}={value}"
            elif value.startswith("[") and value.endswith("]"):
                param_line = f"param {key}={value}"
            else:
                # Assume string parameter, add quotes
                val = value.strip("'\"")
                param_line = f"param {key}='{val}'"
            biceparam_content += f"{os.linesep}{param_line}"

    # Save the new file
    with open(os.path.join(target_path, bicepparam_file_path), "w", encoding="utf-8") as f:
        f.write(biceparam_content)
