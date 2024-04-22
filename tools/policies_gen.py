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

def policies_gen(**kwargs):
    target = kwargs.get("target")
    registry = kwargs.get("registry")
    repository = kwargs.get("repository")
    tag = kwargs.get("tag")

    assert target, "Target is required"
    assert registry, "Registry is required"
    if not repository:
        repository = os.path.splitext(find_bicep_file(target))[0]
        kwargs["repository"] = repository

    bicep_path = os.path.join(target, find_bicep_file(target))
    with open(bicep_path, "r") as file:
        if not any(line.startswith("param ccePolicies array") for line in file):
            print("Bicep template has no policy parameter, skipping generation")
            return

    print("Generating intermediate ARM template as acipolicygen doesn't support bicep")
    with tempfile.TemporaryDirectory() as arm_template_dir:
        arm_template_path = os.path.join(arm_template_dir, "arm.json")
        subprocess.run([
            "az", "bicep", "build",
            "-f", bicep_path,
            "--outfile", arm_template_path
        ], check=True)

        with open(arm_template_path, "r") as file:
            arm_template = json.load(file)

        print("Baking image parameters into template as acipolicygen doesn't support parameters")
        for resource in arm_template["resources"]:
            if resource["type"] == "Microsoft.ContainerInstance/containerGroups":
                resource["properties"]["confidentialComputeProperties"]["ccePolicy"] = ""
                for container in resource["properties"]["containers"]:
                    formatSearch = re.search(r"\[format\('([^']*)'.*\]", container["properties"]["image"])
                    if formatSearch:
                        imageString = formatSearch.group(1)
                        for i, match in enumerate(re.findall(r"parameters\('([^']*)'\)", container["properties"]["image"])):
                            imageString = imageString.replace("{" + str(i) + "}", kwargs.get(match))
                        container["properties"]["image"] = imageString

        with open(arm_template_path, "w") as file:
            json.dump(arm_template, file, indent=2)

        print("Calling acipolicygen and saving policy to file")
        subprocess.run(["az", "extension", "add", "--name", "confcom", "--yes"], check=True)
        res = subprocess.run(["az", "confcom", "acipolicygen",
            "-a", arm_template_path,
            "--outraw",
            "--save-to-file", f"{target}/policy.rego"
        ], check=True, stdout=subprocess.PIPE)

        delimiter = "package policy"
        policies = [delimiter + policy for policy in res.stdout.decode().split(delimiter)[1:]]
        policy_base64 = []
        for idx, policy in enumerate(policies):
            policy_filename = f"{target}/policy_{idx}.rego"
            with open(policy_filename, "w") as file:
                file.write(policy)
            print(f"Saved policy to {policy_filename}")
            policy_base64.append(base64.b64encode(policy.encode()).decode())

    print("Setting the specified registry, tag and policy in the bicep parameters file")
    param_file_path = os.path.join(target, find_bicep_param_file(target))
    aci_param_set(param_file_path, "registry", f"'{registry}'")
    aci_param_set(param_file_path, "repository", f"'{repository}'")
    aci_param_set(param_file_path, "tag", f"'{tag}'")

    aci_param_set(param_file_path, "ccePolicies", "[\n" + "\n".join([
        f"  '{policy}'" for policy in policy_base64
    ]) + "\n]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Security Policies for target")

    parser.add_argument("target",
        help="Target directory", default=os.environ.get("TARGET"),
        nargs="?", # aka Optional
        type=lambda path: os.path.abspath(os.path.expanduser(path)))
    parser.add_argument("--registry",
        help="Container Registry", default=os.environ.get("REGISTRY"))
    parser.add_argument("--repository",
        help="Container Repository", default=os.environ.get("REPOSITORY"))
    parser.add_argument("--tag",
        help="Image Tag", default=os.environ.get("TAG") or "latest")

    args = parser.parse_args()

    policies_gen(
        target=args.target,
        registry=args.registry,
        repository=args.repository,
        tag=args.tag,
    )
