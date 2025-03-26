#!/usr/bin/env python3
import sys
import os
import subprocess
import time
import json
import yaml


def run_cmd(cmd):
    print(f"Running command: {' '.join(cmd)}", flush=True)
    return subprocess.run(
        cmd, stdout=subprocess.PIPE, text=True, check=True
    ).stdout.strip()


def main():
    if len(sys.argv) != 2:
        print(
            f"Usage: {sys.argv[0]} <yaml-file>",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(1)

    yaml_file = sys.argv[1]
    with open(yaml_file, "r") as f:
        yaml_content = f.read()
    yaml_data = yaml.safe_load(yaml_content)
    deployment_name = yaml_data["metadata"]["name"]
    if not deployment_name:
        print(f"Failed to get deployment name from {yaml_file}", flush=True)
        sys.exit(1)
    label_selector_obj = yaml_data["spec"]["selector"]["matchLabels"]
    label_selector = ",".join([f"{k}={v}" for k, v in label_selector_obj.items()])
    print(f"Deployment name: {deployment_name}", flush=True)
    print(f"Label selector: {label_selector}", flush=True)

    # Issue delete
    print(f"Running command: kubectl delete -f {yaml_file}", flush=True)
    res = subprocess.run(
        ["kubectl", "delete", "-f", yaml_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if res.returncode != 0:
        if not "NotFound" in res.stderr:
            print(res.stdout, flush=True)
            print(res.stderr, flush=True, file=sys.stderr)
            print(
                f"Error deleting deployment {deployment_name}",
                flush=True,
            )
            sys.exit(1)
        else:
            print(
                f"Deletion failed with NotFound. Ignoring.",
                flush=True,
            )

    def check_has_pods(verbose=False):
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
                f"Pod {pod_name} - Status: {status}, Start Time: {start_time}",
                flush=True,
            )
            print(f"  Conditions: {', '.join(all_condition_types)}", flush=True)
            if status in not_deleted_states:
                has_pods = True
                if verbose:
                    print("Pod not deleted - info dump follows:\n", flush=True)
                    subprocess.run(["kubectl", "describe", "pod", pod_name])
            else:
                print("Pod exists but status is not running - ignoring.", flush=True)
        return has_pods

    start = time.time()
    print("Waiting 5 min for all pods to be deleted...", flush=True)
    while time.time() - start < 300:
        has_pods = check_has_pods()
        if not has_pods:
            print("No pods left, deletion successful.", flush=True)
            sys.exit(0)
        time.sleep(20)

    check_has_pods(verbose=True)
    sys.exit(1)


if __name__ == "__main__":
    main()
