#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

from c_aci_testing.utils.run_cmd import run_cmd


def vn2_logs(deployment_name: str, **kwargs):
    """
    Fetch logs for all containers in the VN2 deployment.
    """
    # Construct the label selector for the deployment
    label_selector = f"app=tingmao-vn2-{deployment_name}"

    # Run kubectl logs command to fetch logs from all containers
    run_cmd(["kubectl", "logs", "--all-containers", "-l", label_selector, "--tail=-1"], retries=2)

    print(f"Displayed logs for VN2 deployment: {deployment_name}")
