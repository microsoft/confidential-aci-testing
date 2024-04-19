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

from .logging_window import LoggingWindow
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

    with LoggingWindow(
        header=f"\033[35mGenerating security policies for {target}\033[0m",
        prefix="\033[35m| \033[0m",
        max_lines=int(os.environ.get("LOG_LINES", 9999)),
    ) as run_subprocess:

        bicep_path = os.path.join(target, find_bicep_file(target))
        with open(bicep_path, "r") as file:
            if not any(line.startswith("param ccePolicy string") for line in file):
                print("Bicep template has no policy parameter, skipping generation")
                return

        print("Generating intermediate ARM template as acipolicygen doesn't support bicep")
        with tempfile.TemporaryDirectory() as arm_template_dir:
            arm_template_path = os.path.join(arm_template_dir, "arm.json")
            run_subprocess([
                "az", "bicep", "build",
                "-f", bicep_path,
                "--outfile", arm_template_path
            ], check=True)

            with open(arm_template_path, "r") as file:
                arm_template = json.load(file)

            print("Baking image parameters into template as acipolicygen doesn't support parameters")
            dockerfiles = set()
            for filename in os.listdir(target):
                if filename.endswith(".Dockerfile"):
                    dockerfiles.add(os.path.splitext(filename)[0])

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
            run_subprocess(["az", "extension", "add", "--name", "confcom", "--yes"], check=True)
            run_subprocess(["az", "confcom", "acipolicygen",
                "-a", arm_template_path,
                "--outraw",
                "--save-to-file", f"{target}/policy.rego"
            ], check=True)
            print(f"Saved policy to {target}/policy.rego")

        print("Setting the specified registry, tag and policy in the bicep parameters file")
        param_file_path = os.path.join(target, find_bicep_param_file(target))
        aci_param_set(param_file_path, "registry", registry)
        aci_param_set(param_file_path, "repository", repository)
        aci_param_set(param_file_path, "tag", tag)

        with open(f"{target}/policy.rego", "r") as file:
            policy = file.read()
        aci_param_set(param_file_path, "ccePolicy", base64.b64encode(policy.encode()).decode())

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
