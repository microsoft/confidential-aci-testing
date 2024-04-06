#!/usr/bin/env python3

import argparse
import base64
import subprocess
import tempfile
import json
import os
import re
from aci_param_set import update_param
from target_find_files import find_bicep_file, find_bicep_param_file

def policies_gen(**kwargs):
    target = kwargs.get("target")
    registry = kwargs.get("registry")
    repository = kwargs.get("repository")
    tag = kwargs.get("tag")

    if repository is None:
        repository = os.path.splitext(find_bicep_file(target))[0]
        kwargs["repository"] = repository

    print("Generating intermediate ARM template as acipolicygen doesn't support bicep")
    with tempfile.TemporaryDirectory() as arm_template_dir:
        arm_template_path = os.path.join(arm_template_dir, "arm.json")
        subprocess.run([
            "az", "bicep", "build", 
            "-f", os.path.join(target, find_bicep_file(target)),
            "--outfile", arm_template_path
        ])

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
        subprocess.run(["az", "extension", "add", "--name", "confcom", "--yes"])
        subprocess.run(
            [
                "az", "confcom", "acipolicygen",
                "-a", arm_template_path,
                "--outraw", "--save-to-file", f"{target}/policy.rego"
            ]
        )
        print(f"Saved policy to {target}/policy.rego")

    print("Setting the specified registry, tag and policy in the bicep parameters file")
    param_file_path = os.path.join(target, find_bicep_param_file(target))
    update_param(param_file_path, "registry", registry)
    update_param(param_file_path, "repository", repository)
    update_param(param_file_path, "tag", tag)

    with open(f"{target}/policy.rego", "r") as file:
        policy = file.read()
    update_param(param_file_path, "ccePolicy", base64.b64encode(policy.encode()).decode())

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
