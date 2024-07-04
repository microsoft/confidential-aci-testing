#!/usr/bin/env python3

# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import argparse
import base64
import subprocess
import tempfile
import json
import os
import re

from .aci_param_set import aci_param_set
from .target_find_files import find_bicep_file, find_bicep_param_file

def policies_gen(target, deployment_name, subscription, resource_group, registry, repository, tag, debug=False, allow_all=True):

    if debug:
        print("Generating debug policies, this should not be used in production")

    assert registry, "Registry must be set"
    assert tag, "Tag must be set"
    if not repository:
        repository = os.path.splitext(find_bicep_file(target))[0]

    bicep_path = os.path.join(target, find_bicep_file(target))
    with open(bicep_path, "r") as file:
        if not any(line.startswith("param ccePolicies object") for line in file):
            print("Bicep template has no policy parameter, skipping generation")
            return

    print("Setting specified parameters")
    param_file_path = os.path.join(target, find_bicep_param_file(target))

    with open(param_file_path, "r") as file:
        content = file.read().split(os.linesep)

    if any(line.startswith("param registry") for line in content):
        aci_param_set(param_file_path, "registry", f"'{registry}'")
    if any(line.startswith("param repository") for line in content):
        aci_param_set(param_file_path, "repository", f"'{repository}'")
    if any(line.startswith("param tag") for line in content):
        aci_param_set(param_file_path, "tag", f"'{tag}'")

    print("Resolving parameters using what-if deployment")
    res = subprocess.run([
        "az", "deployment", "group", "what-if",
        "--name", deployment_name,
        "--no-pretty-print", "--mode", "Complete",
        *(["--subscription", subscription] if subscription else []),
        "--resource-group", resource_group,
        "--template-file", os.path.join(target, find_bicep_file(target)),
        "--parameters", param_file_path,
    ], check=True, stdout=subprocess.PIPE)

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

                        result["properties"]["confidentialComputeProperties"]["ccePolicy"] = ''
                        container_group_id = result["id"] \
                            .split(prefix)[-1] \
                            .replace(deployment_name, target.split("/")[-1]) \
                            .replace("-", "_")

                        if allow_all:
                            print("Generating an allow all policy")
                            with open(os.path.join(os.path.dirname(__file__), "security_policies", "allow_all.rego"), "r") as policy:
                                policies[container_group_id] = base64.b64encode(policy.read().encode()).decode()
                        else:
                            if "volumes" in result["properties"]:
                                for volume in result["properties"]["volumes"]:
                                    volume["emptyDir"] = {}

                            arm_template_path = os.path.join(arm_template_dir, f"arm_{container_group_id}.json")
                            with open(arm_template_path, "w") as file:
                                json.dump({"resources": [result]}, file, indent=2)

                            print("Calling acipolicygen and saving policy to file")
                            subprocess.run(["az", "extension", "add", "--name", "confcom", "--yes"], check=True)
                            res = subprocess.run(["az", "confcom", "acipolicygen",
                                "-a", arm_template_path,
                                "--outraw",
                                *(["--debug-mode"] if debug else []),
                            ], check=True, stdout=subprocess.PIPE)

                            with open(os.path.join(target, f"policy_{container_group_id}.rego"), "w") as file:
                                file.write(res.stdout.decode())

                            policies[container_group_id] = base64.b64encode(res.stdout).decode()

    if any(line.startswith("param ccePolicies") for line in content):
        aci_param_set(param_file_path, "ccePolicies", "{\n" + "\n".join([
            f"  {group_id}: '{policy}'" for group_id, policy in policies.items()
        ]) + "\n}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Security Policies for target")

    parser.add_argument("target",
        help="Target directory", default=os.environ.get("TARGET"),
        nargs="?", # aka Optional
        type=lambda path: os.path.abspath(os.path.expanduser(path)))
    parser.add_argument("--deployment-name", help="Name of deployment", required=True)
    parser.add_argument(
        "--subscription",
        help="Azure Subscription ID",
        default=os.environ.get("SUBSCRIPTION"),
    )
    parser.add_argument(
        "--resource-group",
        "-g",
        help="Azure Resource Group ID",
        default=os.environ.get("RESOURCE_GROUP"),
    )
    parser.add_argument("--registry",
        help="Container Registry", default=os.environ.get("REGISTRY"))
    parser.add_argument("--repository",
        help="Container Repository", default=os.environ.get("REPOSITORY"))
    parser.add_argument("--tag",
        help="Image Tag", default=os.environ.get("TAG") or "latest")
    parser.add_argument("--debug",
        help="Run in debug mode", action="store_true", default=os.environ.get("DEBUG_IMAGES") == "1")
    parser.add_argument("--allow-all",
        help="Run with allow all policy", action="store_true", default=os.environ.get("ALLOW_ALL") == "1")

    args = parser.parse_args()

    policies_gen(
        target=args.target,
        deployment_name=args.deployment_name,
        subscription=args.subscription,
        resource_group=args.resource_group,
        registry=args.registry,
        repository=args.repository,
        tag=args.tag,
        debug=args.debug,
        allow_all=args.allow_all,
    )
