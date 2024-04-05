#!/usr/bin/env python3

import argparse
import base64
import subprocess
import json
import os
import re
from aci_param_set import update_param

def policies_gen(**kwargs):
    target = kwargs.get("target")

    print("Generating intermediate ARM template as acipolicygen doesn't support bicep")
    subprocess.run(["az", "bicep", "build", "-f", f"{target}/.bicep", "--outfile", "/tmp/arm.json"])

    with open("/tmp/arm.json", "r") as file:
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

    with open("/tmp/arm.json", "w") as file:
        json.dump(arm_template, file, indent=2)

    print("Calling acipolicygen and saving policy to file")
    subprocess.run(["az", "extension", "add", "--name", "confcom", "--yes"])
    subprocess.run(
        [
            "az", "confcom", "acipolicygen",
            "-a", "/tmp/arm.json",
            "--outraw", "--save-to-file", f"{target}/policy.rego"
        ]
    )
    print(f"Saved policy to {target}/policy.rego")

    print("Cleaning up intermediate ARM template")
    os.remove("/tmp/arm.json")

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
        help="Image Tag", default=os.environ.get("TAG"))
    
    args = parser.parse_args()

    policies_gen(
        target=args.target,
        registry=args.registry,
        repository=args.repository,
        tag=args.tag,
    )

    print("Setting the specified registry, tag and policy in the bicep parameters file")
    param_file_path = os.path.join(args.target, ".bicepparam")
    update_param(param_file_path, "registry", args.registry)
    update_param(param_file_path, "repository", args.repository)
    update_param(param_file_path, "tag", args.tag)

    with open(f"{args.target}/policy.rego", "r") as file:
        policy = file.read()
    update_param(param_file_path, "ccePolicy", base64.b64encode(policy.encode()).decode())
