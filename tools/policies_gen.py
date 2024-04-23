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

def policies_gen(target, subscription, resource_group, registry, repository, tag, debug=False):

    if debug:
        print("Generating debug policies, this should not be used in production")

    assert registry, "Registry must be set"
    assert tag, "Tag must be set"
    if not repository:
        repository = os.path.splitext(find_bicep_file(target))[0]

    print("Setting specified parameters")
    param_file_path = os.path.join(target, find_bicep_param_file(target))
    aci_param_set(param_file_path, "registry", f"'{registry}'")
    aci_param_set(param_file_path, "repository", f"'{repository}'")
    aci_param_set(param_file_path, "tag", f"'{tag}'")

    print("Resolving parameters using what-if deployment")
    res = subprocess.run([
        "az", "deployment", "group", "what-if",
        "--no-pretty-print", "--mode", "Complete",
        *(["--subscription", subscription] if subscription else []),
        "--resource-group", resource_group,
        "--template-file", os.path.join(target, find_bicep_file(target)),
        "--parameters", param_file_path,
    ], check=True, stdout=subprocess.PIPE)

    container_group_prefix = "providers/Microsoft.ContainerInstance/containerGroups/"
    policies = []

    with tempfile.TemporaryDirectory() as arm_template_dir:
        resolves_json = json.loads(res.stdout)
        for change in resolves_json["changes"]:
            result = change.get("after")
            if result:
                if container_group_prefix in result["id"]:

                    # Workaround for acipolicygen not supporting empty environment variables
                    for container in result["properties"]["containers"]:
                        for env_var in container.get("environmentVariables", []):
                            if env_var["value"] == "":
                                del env_var["value"]
                                env_var["secureValue"] = ""

                    result["properties"]["confidentialComputeProperties"]["ccePolicy"] = ''
                    container_group_id = result["id"].split(container_group_prefix)[-1]
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

                    policies.append(base64.b64encode(res.stdout).decode())

    aci_param_set(param_file_path, "ccePolicies", "[\n" + "\n".join([
        f"  '{policy}'" for policy in policies
    ]) + "\n]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Security Policies for target")

    parser.add_argument("target",
        help="Target directory", default=os.environ.get("TARGET"),
        nargs="?", # aka Optional
        type=lambda path: os.path.abspath(os.path.expanduser(path)))
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

    args = parser.parse_args()

    policies_gen(
        target=args.target,
        subscription=args.subscription,
        resource_group=args.resource_group,
        registry=args.registry,
        repository=args.repository,
        tag=args.tag,
        debug=args.debug,
    )
