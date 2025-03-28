#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

from c_aci_testing.utils.run_cmd import run_cmd


def vn2_logs(deployment_name: str, follow: bool = False, **kwargs):

    label_selector = f"app={deployment_name}"
    args = ["kubectl", "logs", "--all-containers", "-l", label_selector, "--tail=-1"]
    if follow:
        args.append("-f")

    run_cmd(args, retries=2, consume_stdout=False)
