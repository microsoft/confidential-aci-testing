#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations
import subprocess
import time
import json
import yaml
import sys
import os
import re

from c_aci_testing.utils.run_cmd import run_cmd
from c_aci_testing.utils.find_bicep import find_bicep_files


def vn2_deploy(target_path: str, yaml_path: str, **kwargs):
    """
    Deploy a VN2 application using kubectl apply with the provided YAML file.
    This function also checks that the pods are running correctly after deployment.
    """

    if not yaml_path:
        bicep_file_path, _ = find_bicep_files(target_path)
        bicep_file_name = re.sub(r"\.bicep$", "", os.path.basename(bicep_file_path))
        if not yaml_path:
            yaml_path = os.path.join(target_path, f"{bicep_file_name}.yaml")

    # Load YAML file to get deployment information
    with open(yaml_path, "r") as f:
        yaml_content = f.read()

    yaml_data_all = yaml.safe_load_all(yaml_content)
    all_deployments = [d for d in yaml_data_all if d.get("kind") == "Deployment"]
    if not all_deployments:
        print(f"No deployments found in {yaml_path}")
        sys.exit(1)
    if len(all_deployments) > 1:
        print(f"Multiple deployments found in {yaml_path}, which is not supported.")
        sys.exit(1)
    yaml_data = all_deployments[0]
    deployment_name = yaml_data["metadata"]["name"]
    if not deployment_name:
        print(f"Failed to get deployment name from {yaml_path}")
        sys.exit(1)

    env_dep_name = os.getenv("DEPLOYMENT_NAME")
    if env_dep_name is not None and env_dep_name != deployment_name:
        raise ValueError(
            "Refusing to continue as DEPLOYMENT_NAME environment variable is inconsistent with the deployment name in the YAML file.\n"
            + "This is likely unintentional.\n"
            + "Run c-aci-testing vn2 generate_yaml again."
        )

    label_selector_obj = yaml_data["spec"]["selector"]["matchLabels"]
    label_selector = ",".join([f"{k}={v}" for k, v in label_selector_obj.items()])
    replicas = yaml_data["spec"].get("replicas")
    if not replicas:
        print(f"Failed to get number of replicas from {yaml_path}")
        sys.exit(1)

    annotations = yaml_data["spec"]["template"]["metadata"].get("annotations", {})
    if not annotations.get("microsoft.containerinstance.virtualnode.ccepolicy", ""):
        raise ValueError(
            "YAML does not have a ccepolicy, which will result in non-confidential VN2. Refusing to continue.\n"
            + "Run `c-aci-testing vn2 policygen .` to populate the policy."
        )

    print(f"Deployment name: {deployment_name}")
    print(f"Label selector: {label_selector}")
    print(f"Number of replicas: {replicas}")

    # Deploy the deployment from the YAML template
    run_cmd(["kubectl", "apply", "-f", yaml_path], consume_stdout=False)

    # Wait for all pods of the deployment to be in Running state (max 15 minutes)
    print("Waiting for pods to be in Running state...")
    timeout = time.time() + 900  # 15 minutes

    seen_container_ids_for_pod = {}
    failed_container_ids = set()
    all_container_ids = set()

    def pod_print_conditions(pod):
        conditions = pod.get("status", {}).get("conditions", [])
        all_condition_types = [
            condition.get("type", "???") for condition in sorted(conditions, key=lambda x: x.get("lastTransitionTime"))
        ]
        print(f"  Conditions: {', '.join(all_condition_types)}")

    def check_pod_containers(pod):
        """Check container status and track container IDs to detect restarts."""
        nonlocal seen_container_ids_for_pod
        nonlocal failed_container_ids
        nonlocal all_container_ids

        pod_name = pod["metadata"]["name"]
        pod_container_ids = set()
        has_issue = False
        for container in pod.get("status", {}).get("containerStatuses", []):
            container_id = container.get("containerID")
            container_name = container.get("name", "???")
            image_id = container.get("imageID", "???")
            restart_count = container.get("restartCount", 0)
            if not container_id:
                print(
                    f"  !: Container ID not found for container {container_name} in pod {pod_name}. Pod being restarted?"
                )
                continue
            pod_container_ids.add(container_id)
            all_container_ids.add(container_id)
            print(f"  Container {container_name}:")
            print(f"    ID: {container_id}")
            print(f"    Image ID: {image_id}")
            print(f"    Restart Count: {restart_count}")
            if restart_count > 0:
                print(f"    !: Container {container_name} has restarted {restart_count} times!")
                has_issue = True
        if pod_name in seen_container_ids_for_pod:
            for container_id in seen_container_ids_for_pod[pod_name]:
                if container_id not in pod_container_ids:
                    print(
                        f"    !: Container ID {container_id}, which appeared in a previous check of pod {pod_name}, has now disappeared"
                    )
                    failed_container_ids.add(container_id)
        if pod_container_ids:
            seen_container_ids_for_pod[pod_name] = pod_container_ids
        return has_issue

    nb_pods_running = 0

    while time.time() < timeout:
        pods_json = run_cmd(["kubectl", "get", "pods", "-l", label_selector, "-o", "json"], retries=2)
        assert pods_json
        pods_data = json.loads(pods_json)
        if not pods_data.get("items"):
            print("No pods created yet.")
            time.sleep(5)
            continue

        has_issue = False
        nb_pods_running = 0
        for pod in pods_data["items"]:
            print(f"Pod {pod['metadata']['name']} status: {pod['status']['phase']}")
            pod_print_conditions(pod)
            if pod.get("status", {}).get("phase") == "Running":
                nb_pods_running += 1
                if check_pod_containers(pod):
                    print(f"ERROR: Issue detected for pod {pod['metadata']['name']}. Pod info dump follows:")
                    subprocess.run(
                        ["kubectl", "describe", "pod", pod["metadata"]["name"]],
                        check=True,
                    )
                    has_issue = True
        if has_issue:
            print("Exiting due to issues detected during startup.")
            sys.exit(1)
        if nb_pods_running == replicas:
            print("All pods are running now.")
            break
        if nb_pods_running > replicas:
            print(f"Error: More pods running ({nb_pods_running}) than expected ({replicas}).")
            sys.exit(1)

        print("Waiting for all pods to be running...")
        time.sleep(5)

    if nb_pods_running < replicas:
        print("Timeout reached: not all pods are Running.")
        sys.exit(1)

    # Final check for any failed containers that may have been replaced
    if failed_container_ids:
        print("ERROR: No restart count > 0 on any pods, but we have observed container IDs that have disappeared.")
        for container_id in failed_container_ids:
            print(f"  Container ID: {container_id}")
        print("Search in earlier logs for more information.")
        sys.exit(1)

    print(f"VN2 deployment successful: {deployment_name}")
    print("All pods are running. You can monitor them by using the 'vn2 logs' command.")
