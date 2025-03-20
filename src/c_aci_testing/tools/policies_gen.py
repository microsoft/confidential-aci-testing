#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations

import base64
import json
import os
import pathlib
import re
import subprocess
import tempfile
import shutil

from .aci_param_set import aci_param_set


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


def policies_gen(
    target_path: str,
    deployment_name: str,
    subscription: str,
    resource_group: str,
    registry: str,
    repository: str | None,
    tag: str | None,
    policy_type: str,
    fragments_json: str | None = None,
    infrastructure_svn: int | None = None,
    **kwargs,
):

    # Inform the user of the policy type
    print(f"Using the policy type: {policy_type}")
    if policy_type == "none":
        print("Skipping policy generation")
        return
    if policy_type != "generated":
        print("This should not be used in real environments")

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

    # Check if a policy needs to be set
    with open(bicep_file_path) as f:
        bicep_template = f.read()
    if "param ccePolicies object" not in bicep_template:
        print("This template doesn't use generated policies, skipping policy gen")
        return

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

    policies = {}
    arm_template_dir = tempfile.mkdtemp()
    print(f"Placing ARM templates in {arm_template_dir}")

    print("Converting bicep files to an ARM template")
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

    for resource in arm_template_json["resources"]:

        # Only handle container groups
        if resource["type"] not in (
            "Microsoft.ContainerInstance/containerGroups",
            "Microsoft.ContainerInstance/containerGroupProfiles",
        ):
            continue

        # Only handle confidential container groups
        if resource["properties"].get("sku", "Standard") != "Confidential":
            continue

        # Workaround for acipolicygen not supporting empty environment variables
        for container in resource["properties"]["containers"]:
            for env_var in container["properties"].get("environmentVariables", []):
                if "value" in env_var and env_var["value"] == "":
                    del env_var["value"]
                if "value" not in env_var:
                    env_var["secureValue"] = ""

        # Derive container group ID
        container_group_id = (
            resource["name"]
            .replace(
                deployment_name,
                pathlib.Path(bicep_file_path).stem,
            )
            .replace("-", "_")
        )

        allow_all_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "templates",
            "allow_all_policy.rego",
        )
        if policy_type == "allow_all":
            with open(allow_all_path, encoding="utf-8") as policy_file:
                policy = policy_file.read()
        else:

            # Write the resource to an ARM template file
            arm_template_path = os.path.join(arm_template_dir, f"arm_{container_group_id}.json")
            with open(arm_template_path, "w", encoding="utf-8") as file:
                json.dump({"resources": [resource]}, file, indent=2)

            print("Calling acipolicygen and saving policy to file")
            subprocess.run(["az", "extension", "add", "--name", "confcom", "--yes"], check=True)
            args = [
                "az",
                "confcom",
                "acipolicygen",
                "-a",
                arm_template_path,
                "--outraw-pretty-print",
                *(["--debug-mode"] if policy_type == "debug" else []),
                *(["--include-fragments", "--fragments-json", fragments_json] if fragments_json else []),
                *(["--infrastructure-svn", str(infrastructure_svn)] if infrastructure_svn is not None else []),
            ]
            print("Running: " + " ".join(args))
            res = subprocess.run(
                args,
                check=True,
                stdout=subprocess.PIPE,
            )
            policy = res.stdout.decode()

        with open(os.path.join(target_path, f"policy_{container_group_id}.rego"), "w") as file:
            file.write(policy)

        policies[container_group_id] = base64.b64encode(policy.encode()).decode()

    aci_param_set(
        target_path,
        parameters=[
            "ccePolicies="
            + "{\n"
            + "\n".join([f"  {group_id}: '{policy}'" for group_id, policy in policies.items()])
            + "\n}"
        ],
    )

    print(f"Removing {arm_template_dir}")
    shutil.rmtree(arm_template_dir)
