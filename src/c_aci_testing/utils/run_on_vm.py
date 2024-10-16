#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations

import subprocess
import json


def run_on_vm(
    vm_name: str,
    resource_group: str,
    command: str,
):
    print(f"Running command on VM: {command}")
    res = subprocess.run(
        [
            "az",
            "vm",
            "run-command",
            "invoke",
            "-g",
            resource_group,
            "-n",
            vm_name,
            "--command-id",
            "RunPowerShellScript",
            "--scripts",
            command,
        ],
        check=True,
        stdout=subprocess.PIPE,
    )
    out = json.loads(res.stdout)

    stderr = ""
    for value in out["value"]:
        if "StdErr" in value["code"]:
            stderr = value["message"]

    stdout = None
    for value in out["value"]:
        if "StdOut" in value["code"]:
            stdout = value["message"]

    if stderr:
        print(f"StdErr:\n{stderr}")
    if stdout:
        print(stdout)

    if stdout is None:
        raise Exception("No StdOut in response")

    return stdout
