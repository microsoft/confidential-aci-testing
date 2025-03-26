#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations

import json
import os
import subprocess
import sys
import re
from typing import Iterable, Tuple

from c_aci_testing.tools.aci_param_set import aci_param_set
from c_aci_testing.utils.find_bicep import find_bicep_files


def resolve_arm_functions(arm_template_str, resource_group, subscription, deployment_name):

    # Handle constants
    for constant, value in [
        ("resourceGroup().name", resource_group),
        ("subscription().subscriptionId", subscription),
        ("deployment().name", deployment_name),
    ]:
        arm_template_str = arm_template_str.replace(constant, value)

    # Remove the square brackets which denote functions in ARM templates
    # since they will be resolved. Do it here so parameters are correctly resolved.
    arm_template_lines = arm_template_str.split("\\n")
    for idx, line in enumerate(arm_template_lines):
        arm_template_lines[idx] = re.sub(r'\\"\[(.*?)\]\\"', r"\"\1\"", line)
    arm_template_str = "\\n".join(arm_template_lines)
    arm_template_dict = json.loads(json.loads(arm_template_str)["templateJson"])

    # Handle parameters function
    parameters_dict = {
        key: value["value"]
        for key, value in json.loads(json.loads(arm_template_str)["parametersJson"])["parameters"].items()
    }
    parameters = {key: definition.get("defaultValue") for key, definition in arm_template_dict["parameters"].items()}
    parameters.update(parameters_dict)
    for key, value in parameters.items():
        arm_template_str = re.sub(
            f"parameters\\('{key}'\\)",
            str(value),
            arm_template_str,
        )

    # Handle empty function
    arm_template_lines = arm_template_str.split("\\n")
    for idx, line in enumerate(arm_template_lines):
        for match in re.findall(r"empty\((.*?)\)", line):
            arm_template_lines[idx] = line.replace(
                f"empty({match})",
                "true" if match == "" else "false",
            )
            line = arm_template_lines[idx]
    arm_template_str = "\\n".join(arm_template_lines)

    # Handle if function
    arm_template_lines = arm_template_str.split("\\n")
    for idx, line in enumerate(arm_template_lines):
        for condition, if_true, if_false in re.findall(
            r"if\((.*?)\, (.*?)\, (.*?)\)",
            line,
        ):
            arm_template_lines[idx] = line.replace(
                f"if({condition}, {if_true}, {if_false})",
                f"{if_true}" if condition == "true" else f"{if_false}",
            )
            line = arm_template_lines[idx]
    arm_template_str = "\\n".join(arm_template_lines)

    # Handle format function
    arm_template_lines = arm_template_str.split("\\n")
    for idx, line in enumerate(arm_template_lines):
        for format_string, inputs in re.findall(r"format\((.*?)\, (.*?)\)", line):
            inputs_list = [i.strip("'") for i in inputs.split(", ")]
            arm_template_lines[idx] = line.replace(
                f"format({format_string}, {inputs})",
                format_string.format(*inputs_list).strip("'"),
            )
    arm_template_str = "\\n".join(arm_template_lines)

    return json.loads(json.loads(arm_template_str)["templateJson"])


def parse_bicep(
    target_path: str,
    subscription: str,
    resource_group: str,
    deployment_name: str,
    registry: str,
    repository: str | None,
    tag: str | None,
) -> dict:
    """
    Returns ARM template JSON with parameters inlined
    """

    _, bicepparam_file_path = find_bicep_files(target_path)

    # Set required parameters in bicep param file
    aci_param_set(
        target_path,
        parameters=[
            f"{k}='{v}'"
            for k, v in {
                "registry": registry,
                "repository": repository or "",
                "tag": tag or "",
            }.items()
        ],
        add=False,  # If the user removed a field, don't re-add it
    )

    print("Converting bicep files to an ARM template", flush=True)
    sys.stderr.flush()
    res = subprocess.run(
        [
            "az",
            "bicep",
            "build-params",
            "--file",
            bicepparam_file_path,
            "--stdout",
        ],
        check=True,
        stdout=subprocess.PIPE,
    )
    arm_template_json = resolve_arm_functions(
        res.stdout.decode(),
        resource_group=resource_group,
        subscription=subscription,
        deployment_name=deployment_name,
    )

    return arm_template_json


def arm_template_for_each_container_group(
    arm_template_json: dict,
) -> Iterable[Tuple[dict, Iterable[dict]]]:
    """
    Return an iterater of tuples:
        (container_group_resource_json, containers)
    where:
        - container_group_resource_json is the ARM JSON for a container group
        - containers is an iterable of the containers in the container group
    """

    for resource in arm_template_json["resources"]:
        # Only handle container groups
        if resource["type"] not in (
            "Microsoft.ContainerInstance/containerGroups",
            "Microsoft.ContainerInstance/containerGroupProfiles",
        ):
            continue

        def get_containers(group) -> Iterable[dict]:
            if "containers" in group["properties"]:
                for container in group["properties"]["containers"]:
                    yield container

        yield resource, get_containers(resource)


def arm_template_for_each_container_group_with_fixup(
    arm_template_json: dict,
) -> Iterable[Tuple[dict, Iterable[dict]]]:
    """
    Same interface as arm_template_for_each_container_group, but with some
    acipolicygen workarounds
    """

    for resource, containers in arm_template_for_each_container_group(arm_template_json):

        containers = list(containers)

        # Workaround for acipolicygen not supporting empty environment variables
        for container in containers:
            for env_var in container["properties"].get("environmentVariables", []):
                if "value" in env_var and env_var["value"] == "":
                    del env_var["value"]
                if "value" not in env_var:
                    env_var["secureValue"] = ""

        yield resource, containers
