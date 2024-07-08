#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile

from .aci_param_set import aci_param_set


def policies_gen(
    target_path: str,
    deployment_name: str,
    subscription: str,
    resource_group: str,
    registry: str,
    repository: str,
    tag: str,
    policy_type: str,
    **kwargs,
):

    # Inform the user of the policy type
    print(f"Using the policy type: {policy_type}")
    if policy_type == "none":
        print("Skipping policy generation")
        return
    if policy_type != "generated":
        print("This should not be used in real environments")

    # Find the bicep files
    for file in os.listdir(target_path):
        if file.endswith(".bicep"):
            bicep_file_path = os.path.join(target_path, file)
        elif file.endswith(".bicepparam"):
            bicepparam_file_path = os.path.join(target_path, file)

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
                "repository": repository,
                "tag": tag,
            }.items()
        ],
        add=False,  # If the user removed a field, don't re-add it
    )

    # Create an ARM template with parameters resolved
    print("Resolving parameters using what-if deployment")
    res = subprocess.run(
        [
            "az",
            "deployment",
            "group",
            "what-if",
            "--name",
            deployment_name,
            "--no-pretty-print",
            "--mode",
            "Complete",
            "--subscription",
            subscription,
            "--resource-group",
            resource_group,
            "--template-file",
            bicep_file_path,
            "--parameters",
            bicepparam_file_path,
        ],
        check=True,
        stdout=subprocess.PIPE,
    )

    policies = {}

    with tempfile.TemporaryDirectory() as arm_template_dir:
        resolves_json = json.loads(res.stdout)
        for change in resolves_json["changes"]:
            result = change.get("after")
            if result:
                for prefix in (
                    "providers/Microsoft.ContainerInstance/containerGroups/",
                    "providers/Microsoft.ContainerInstance/containerGroupProfiles/",
                ):
                    if prefix in result["id"]:

                        # Workaround for acipolicygen not supporting empty environment variables
                        for container in result["properties"]["containers"]:
                            for env_var in container["properties"].get("environmentVariables", []):
                                if "value" in env_var and env_var["value"] == "":
                                    del env_var["value"]
                                if "value" not in env_var:
                                    env_var["secureValue"] = ""

                        if "confidentialComputeProperties" not in result["properties"]:
                            result["properties"]["confidentialComputeProperties"] = {}

                        result["properties"]["confidentialComputeProperties"]["ccePolicy"] = ""
                        container_group_id = (
                            result["id"]
                            .split(prefix)[-1]
                            .replace(deployment_name, bicep_file_path.split("/")[-1].split(".")[0])
                            .replace("-", "_")
                        )

                        if policy_type == "allow_all":
                            with open(
                                os.path.join(os.path.dirname(__file__), "security_policies", "allow_all.rego")
                            ) as policy_file:
                                policy = policy_file.read()
                        else:
                            if "volumes" in result["properties"]:
                                for volume in result["properties"]["volumes"]:
                                    volume["emptyDir"] = {}

                            arm_template_path = os.path.join(arm_template_dir, f"arm_{container_group_id}.json")
                            with open(arm_template_path, "w") as file:
                                json.dump({"resources": [result]}, file, indent=2)

                            print("Calling acipolicygen and saving policy to file")
                            subprocess.run(["az", "extension", "add", "--name", "confcom", "--yes"], check=True)
                            res = subprocess.run(
                                [
                                    "az",
                                    "confcom",
                                    "acipolicygen",
                                    "-a",
                                    arm_template_path,
                                    "--outraw",
                                    *(["--debug-mode"] if policy_type == "debug" else []),
                                ],
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
