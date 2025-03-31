#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations
import subprocess
import time
import json
import sys

from c_aci_testing.utils.run_cmd import run_cmd

def vn2_remove(deployment_name: str, **kwargs):
    """
    Remove a VN2 deployment and verify that all pods are cleaned up.
    """
    print(f"Removing VN2 deployment: {deployment_name}")

    # First, get the pod label selector for monitoring
    try:
        deployment_json = run_cmd(["kubectl", "get", "deployment", deployment_name, "-o", "json"], retries=2)
        deployment_data = json.loads(deployment_json)
        label_selector_obj = deployment_data["spec"]["selector"]["matchLabels"]
        label_selector = ",".join([f"{k}={v}" for k, v in label_selector_obj.items()])
        print(f"Label selector: {label_selector}")
    except subprocess.CalledProcessError:
        print(f"Warning: Couldn't get label selector for deployment {deployment_name}. Deployment might not exist.")
        label_selector = f"app={deployment_name}"
        print(f"Using default label selector: {label_selector}")

    # Delete the deployment using kubectl
    try:
        print(f"Deleting deployment {deployment_name}")
        result = subprocess.run(
            ["kubectl", "delete", f"deployments/{deployment_name}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            if "NotFound" in result.stderr:
                print(f"Deployment {deployment_name} not found. It may have been already deleted.")
            else:
                print(result.stdout)
                print(result.stderr)
                print(f"Error deleting deployment {deployment_name}")
                sys.exit(1)
    except Exception as e:
        print(f"Error deleting deployment: {str(e)}")
        sys.exit(1)

    def check_has_pods(verbose=False):
        """Check if any pods with the deployment label still exist."""
        try:
            pods_json = run_cmd(
                ["kubectl", "get", "pods", "-l", label_selector, "-o", "json"]
            )
            pods_data = json.loads(pods_json)
            has_pods = False
            not_deleted_states = ["Running", "Pending", "ContainerCreating", "Terminating"]
            for pod in pods_data.get("items", []):
                pod_name = pod["metadata"]["name"]
                status = pod.get("status", {}).get("phase", "Unknown")
                conditions = pod.get("status", {}).get("conditions", [])
                all_condition_types = [
                    condition.get("type", "???")
                    for condition in sorted(
                        conditions, key=lambda x: x.get("lastTransitionTime")
                    )
                ]
                start_time = pod.get("status", {}).get("startTime", "???")
                print(
                    f"Pod {pod_name} - Status: {status}, Start Time: {start_time}"
                )
                print(f"  Conditions: {', '.join(all_condition_types)}")
                if status in not_deleted_states:
                    has_pods = True
                    if verbose:
                        print("Pod not deleted - info dump follows:\n")
                        subprocess.run(["kubectl", "describe", "pod", pod_name])
                else:
                    print("Pod exists but status is not running - ignoring.")
            return has_pods
        except subprocess.CalledProcessError:
            print("Error checking for pods. This might mean they're already gone.")
            return False

    # Wait for all pods to be deleted (timeout after 5 minutes)
    start = time.time()
    print("Waiting for all pods to be deleted...")
    while time.time() - start < 300:  # 5 minutes timeout
        has_pods = check_has_pods()
        if not has_pods:
            print("No pods left, deletion successful.")
            return
        time.sleep(20)

    # If we get here, the pods weren't deleted within the timeout period
    check_has_pods(verbose=True)
    print("Warning: Some pods may still exist after timeout period.")
    sys.exit(1)
