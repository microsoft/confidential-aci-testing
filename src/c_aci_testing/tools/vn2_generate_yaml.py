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
    repository: str,
    tag: str,
    replicas: int,
    **kwargs,
):
    bicep_file_path, _ = find_bicep_files(target_path)
    bicep_file_name = re.sub(r"\.bicep$", "", os.path.basename(bicep_file_path))
    if not yaml_path:
        yaml_path = os.path.join(target_path, f"{bicep_file_name}.yaml")

    aci_param_set(
        target_path,
        parameters=[
            f"{k}='{v}'"
            for k, v in {
                "managedIDName": managed_identity,
            }.items()
        ],
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

    annotations = {}
    containers = []

    template_spec = {
        "containers": containers,
        "nodeSelector": {"virtualization": "virtualnode2"},
        "tolerations": [{"key": "virtual-kubelet.io/provider", "operator": "Exists", "effect": "NoSchedule"}],
    }

    yaml_body = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": deployment_name,
        },
        "spec": {
            "replicas": replicas,
            "selector": {
                "matchLabels": {
                    "app": deployment_name,
                },
            },
            "template": {
                "metadata": {
                    "labels": {
                        "app": deployment_name,
                    },
                    "annotations": annotations,
                },
                "spec": template_spec,
            },
        },
    }

    container_groups = list(arm_template_for_each_container_group(arm_template_json))

    if not container_groups:
        raise ValueError("No container groups found in the ARM template")
    if len(container_groups) > 1:
        # To avoid problems with create_vn2_deployment_checked.py
        raise ValueError("This does not support multiple container groups yet")

    container_group, arm_containers = container_groups[0]

    annotations["microsoft.containerinstance.virtualnode.ccepolicy"] = (
        container_group["properties"].get("confidentialComputeProperties", {}).get("ccePolicy", "")
    )
    if "zones" in container_group:
        annotations["microsoft.containerinstance.virtualnode.zones"] = ",".join(container_group["zones"])

    identity = container_group.get("identity", {})
    if "UserAssigned" in identity.get("type", ""):
        annotations["microsoft.containerinstance.virtualnode.identity"] = list(
            identity["userAssignedIdentities"].keys()
        )[0]

    if "subnetIds" in container_group["properties"]:
        armSubnetIds = container_group["properties"]["subnetIds"]
        if len(armSubnetIds) > 1:
            raise ValueError("VN2 does not support multiple subnets")
        annotations["microsoft.containerinstance.virtualnode.subnets.primary"] = armSubnetIds[0]["id"]

    for arm_container in arm_containers:
        props = arm_container.get("properties", {})

        container_def = {"name": arm_container.get("name"), "image": props.get("image")}
        containers.append(container_def)

        resources = props.get("resources", {}).get("requests", {})
        container_def["resources"] = {"requests": {"cpu": resources.get("cpu"), "memory": resources.get("memoryInGB")}}

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
                print(f"Creating short-lived pull secret {secret_name}", flush=True)
                vn2_create_pull_secret(registry)

    yaml_str = yaml.dump(yaml_body, sort_keys=False)

    # Write the YAML to the output file
    with open(yaml_path, "wt") as f:
        f.write(yaml_str)
