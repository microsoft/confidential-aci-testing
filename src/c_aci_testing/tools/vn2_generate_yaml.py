#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import json
import os
import pathlib
import yaml
import re

from c_aci_testing.utils.parse_bicep import parse_bicep, arm_template_for_each_container_group
from c_aci_testing.utils.find_bicep import find_bicep_files
from c_aci_testing.tools.aci_param_set import aci_param_set
from .vn2_create_pull_secret import get_pull_secret_name, vn2_create_pull_secret


def vn2_generate_yaml(
    target_path: str,
    yaml_path: str,
    subscription: str,
    resource_group: str,
    deployment_name: str,
    managed_identity: str,
    registry: str,
    repository: str | None,
    tag: str | None,
    replicas: int,
    **kwargs,
):
    bicep_file_path, _ = find_bicep_files(target_path)
    bicep_file_name = re.sub(r"\.bicep$", "", os.path.basename(bicep_file_path))

    aci_param_set(
        target_path,
        parameters={
            "managedIDName": managed_identity,
        },
        add=False,
    )

    arm_template_json = parse_bicep(
        target_path,
        subscription,
        resource_group,
        deployment_name,
        registry,
        repository,
        tag,
    )

    container_groups = list(arm_template_for_each_container_group(arm_template_json))
    if not container_groups:
        raise ValueError("No container groups found in the ARM template")

    if yaml_path and len(container_groups) > 1:
        raise ValueError("Cannot specify single YAML output path when multiple container groups are present")

    # Track created pull secrets to avoid redundant API calls
    created_pull_secrets = set()

    for container_group, arm_containers in container_groups:
        pod_name = deployment_name
        if len(container_groups) > 1:
            pod_name = container_group["name"]

        annotations = {
            # This is needed to get rid of the "nameserver 10.0.0.10" in
            # /etc/resolv.conf.
            # Otherwise, every web request will fail / hang for 30 seconds, since
            # the cluster DNS is not reachable from the ACI instance.
            # https://github.com/azure-core-compute/VirtualNodesOnACI-1P/blob/main/Docs/PodCustomizations.md#disable-k8s-dns-injection
            "microsoft.containerinstance.virtualnode.injectdns": "false",
        }

        containers = []
        extra_resources = []

        template_spec = {
            "containers": containers,
            "nodeSelector": {"virtualization": "virtualnode2"},
            "tolerations": [{"key": "virtual-kubelet.io/provider", "operator": "Exists", "effect": "NoSchedule"}],
        }

        pod_deployment = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": pod_name,
            },
            "spec": {
                "replicas": replicas,
                "selector": {
                    "matchLabels": {
                        "app": pod_name,
                    },
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": pod_name,
                        },
                        "annotations": annotations,
                    },
                    "spec": template_spec,
                },
            },
        }

        annotations["microsoft.containerinstance.virtualnode.ccepolicy"] = (
            container_group["properties"].get("confidentialComputeProperties", {}).get("ccePolicy", "")
        )
        if container_group.get("zones"):
            annotations["microsoft.containerinstance.virtualnode.zones"] = ",".join(container_group["zones"])

        identity = container_group.get("identity", {})
        if "UserAssigned" in identity.get("type", ""):
            annotations["microsoft.containerinstance.virtualnode.identity"] = list(
                identity["userAssignedIdentities"].keys()
            )[0]

        if "subnetIds" in container_group["properties"]:
            armSubnetIds = container_group["properties"]["subnetIds"]
            if armSubnetIds is not None:
                if len(armSubnetIds) > 1:
                    raise ValueError("VN2 does not support multiple subnets")
                elif len(armSubnetIds) == 1:
                    annotations["microsoft.containerinstance.virtualnode.subnets.primary"] = armSubnetIds[0]["id"]
                else:
                    print(
                        "Warning: using vn2 implies vnet, but subnetIds is specified as an empty array. Container group will still use the AKS vnet."
                    )

        for arm_container in arm_containers:
            props = arm_container.get("properties", {})

            container_def = {"name": arm_container.get("name"), "image": props.get("image")}
            containers.append(container_def)

            resources = props.get("resources", {}).get("requests", {})
            memoryStr = f"{resources.get('memoryInGB')}G"
            container_def["resources"] = {"requests": {"cpu": resources.get("cpu"), "memory": memoryStr}}

            ports = props.get("ports", [])
            if ports:
                container_def["ports"] = [{"containerPort": port.get("port")} for port in ports]

            env = props.get("environmentVariables", [])
            if env:
                container_def["env"] = [
                    {"name": var.get("name"), "value": var.get("value", var.get("secureValue"))} for var in env
                ]

            if "command" in props:
                container_def["command"] = props["command"]

        if registry:
            secret_name = get_pull_secret_name(registry)
            if secret_name:
                template_spec["imagePullSecrets"] = [{"name": secret_name}]
                # Only create the pull secret if it hasn't been created yet
                if secret_name not in created_pull_secrets:
                    print(f"Creating short-lived pull secret {secret_name}", flush=True)
                    vn2_create_pull_secret(registry)
                    created_pull_secrets.add(secret_name)

        if container_group["properties"].get("ipAddress", {}).get("type") == "Public":
            ports = {"port": p["port"] for p in container_group["properties"]["ipAddress"]["ports"]}
            service = {
                "apiVersion": "v1",
                "kind": "Service",
                "metadata": {
                    "name": pod_name,
                    "annotations": {
                        "external-dns.alpha.kubernetes.io/hostname": f"{pod_name}.azure.net",
                        "external-dns.alpha.kubernetes.io/internal-hostname": f"clusterip.{pod_name}.azure.net",
                    },
                },
                "spec": {
                    "type": "LoadBalancer",
                    "ports": [ports],
                    "selector": {"app": pod_name},
                },
            }
            extra_resources.append(service)

        yaml_str = yaml.dump_all([pod_deployment, *extra_resources], sort_keys=False)

        if len(container_groups) == 1:
            if not yaml_path:
                yaml_path = os.path.join(target_path, f"{bicep_file_name}.yaml")
            # else use provided yaml_path
        else:
            yaml_path = os.path.join(
                target_path,
                f"{container_group['name']}.yaml",
            )

        # Write the YAML to the output file
        with open(yaml_path, "wt") as f:
            f.write(yaml_str)
