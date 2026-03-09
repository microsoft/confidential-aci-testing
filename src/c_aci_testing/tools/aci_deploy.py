#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import json
import os
import subprocess
import sys
import time

from .aci_param_set import aci_param_set


def aci_deploy(
    target_path: str,
    deployment_name: str,
    subscription: str,
    resource_group: str,
    location: str,
    managed_identity: str,
    timeout: int = 0,
    deploy_output_file: str = "",
    **kwargs,
) -> list[str]:
    # Set required parameters in bicep param file
    aci_param_set(
        target_path,
        parameters={
            "location": location,
            "managedIDName": managed_identity,
        },
        add=False,
    )

    bicep_file_path = None
    bicepparam_file_path = None

    # Find the bicep files
    for file in os.listdir(target_path):
        if file.endswith(".bicep"):
            bicep_file_path = os.path.join(target_path, file)
        elif file.endswith(".bicepparam"):
            bicepparam_file_path = os.path.join(target_path, file)

    if not bicep_file_path:
        raise FileNotFoundError(f"No bicep file found in {target_path}")
    if not bicepparam_file_path:
        raise FileNotFoundError(f"No bicepparam file found in {target_path}")

    az_command = [
        "az",
        "deployment",
        "group",
        "create",
        "-n",
        deployment_name,
        "--subscription",
        subscription,
        "--resource-group",
        resource_group,
        "--template-file",
        os.path.join(target_path, bicep_file_path),
        "--parameters",
        bicepparam_file_path,
        "--no-wait",
    ]

    print(f"{os.linesep}Deploying to Azure, view deployment here:")
    print("%2F".join([
        "https://ms.portal.azure.com/#blade/HubsExtension/DeploymentDetailsBlade/id/",
        "subscriptions", subscription,
        "resourceGroups", resource_group,
        "providers", "Microsoft.Resources", "deployments", deployment_name,
    ]))
    print("")

    sys.stdout.flush()
    sys.stderr.flush()

    res = subprocess.run(az_command)
    if res.returncode != 0:
        raise RuntimeError(f"Deployment failed with return code {res.returncode}")

    start_time = time.time()
    correlation_id = None
    consecutive_failures = 0

    while True:
        elapsed = time.time() - start_time
        if timeout > 0 and elapsed >= timeout:
            # One final check before timing out
            show_result = _show_deployment(deployment_name, subscription, resource_group)
            if show_result is not None:
                state = show_result.get("properties", {}).get("provisioningState", "")
                if state == "Succeeded":
                    return _handle_success(show_result, start_time, deploy_output_file)
            print(json.dumps(show_result, indent=2) if show_result else "No deployment data available")
            error_msg = f"Deployment timed out after {timeout}s"
            _write_output_file(deploy_output_file, error=error_msg, correlation_id=correlation_id)
            raise RuntimeError(error_msg)

        time.sleep(15)

        show_result = _show_deployment(deployment_name, subscription, resource_group)

        if show_result is None:
            consecutive_failures += 1
            if consecutive_failures >= 3:
                error_msg = "Failed to query deployment status 3 consecutive times"
                _write_output_file(deploy_output_file, error=error_msg, correlation_id=correlation_id)
                raise RuntimeError(error_msg)
            continue

        consecutive_failures = 0

        if correlation_id is None:
            correlation_id = show_result.get("properties", {}).get("correlationId", "")
            if correlation_id:
                print(f"Deployment created with correlation ID: {correlation_id}")

        state = show_result.get("properties", {}).get("provisioningState", "")

        if state == "Succeeded":
            return _handle_success(show_result, start_time, deploy_output_file)
        elif state != "Running" and state != "Accepted":
            print(json.dumps(show_result, indent=2))
            error_msg = f"Deployment failed with provisioningState: {state}"
            _write_output_file(deploy_output_file, error=error_msg, correlation_id=correlation_id)
            raise RuntimeError(error_msg)


def _show_deployment(deployment_name: str, subscription: str, resource_group: str) -> dict | None:
    try:
        res = subprocess.run(
            [
                "az",
                "deployment",
                "group",
                "show",
                "-n",
                deployment_name,
                "--subscription",
                subscription,
                "-g",
                resource_group,
                "-o",
                "json",
            ],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return json.loads(res.stdout)
    except subprocess.CalledProcessError as e:
        print(
            f"Failed to query deployment status for {deployment_name} in resource group {resource_group}: {e.stderr}",
            file=sys.stderr,
            flush=True,
        )
        return None


def _handle_success(show_result: dict, start_time: float, deploy_output_file: str) -> list[str]:
    duration_ms = int((time.time() - start_time) * 1000)
    correlation_id = show_result.get("properties", {}).get("correlationId", "")

    ids = show_result.get("properties", {}).get("outputs", {}).get("ids", {}).get("value", [])

    for id in ids:
        print(f'Deployed {os.linesep}{id.split("/")[-1]}, view here:')
        print(f"https://ms.portal.azure.com/#@microsoft.onmicrosoft.com/resource{id}")

    _write_output_file(
        deploy_output_file,
        correlation_id=correlation_id,
        duration_ms=duration_ms,
    )

    return ids


def _write_output_file(
    deploy_output_file: str,
    error: str | None = None,
    correlation_id: str | None = None,
    duration_ms: int = 0,
):
    if not deploy_output_file:
        return
    if error is not None:
        output_data = {"error": error, "correlationId": correlation_id}
    else:
        output_data = {
            "correlationId": correlation_id,
            "durationMs": duration_ms,
            "error": None,
        }
    with open(deploy_output_file, "w") as f:
        json.dump(output_data, f, indent=2)
