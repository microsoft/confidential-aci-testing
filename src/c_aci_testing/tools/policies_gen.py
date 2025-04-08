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
import sys
import tempfile

from .aci_param_set import aci_param_set
from c_aci_testing.utils.parse_bicep import (
    find_bicep_files,
    arm_template_for_each_container_group_with_fixup,
    parse_bicep,
)

ALLOW_ALL_POLICY_REGO_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "templates",
    "allow_all_policy.rego",
)


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

    bicep_file_path, _ = find_bicep_files(target_path)

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

    arm_template_json = parse_bicep(target_path, subscription, resource_group, deployment_name)

    policies = {}

    for container_group, containers in arm_template_for_each_container_group_with_fixup(
        arm_template_json,
    ):
        # Derive container group ID
        # This is used in the ccePolicies object.
        container_group_id = (
            container_group["name"]
            .replace(
                deployment_name,
                pathlib.Path(bicep_file_path).stem,
            )
            .replace("-", "_")
        )

        # Only handle confidential container groups
        if container_group["properties"].get("sku", "Standard") != "Confidential":
            continue

        if policy_type == "allow_all":
            with open(ALLOW_ALL_POLICY_REGO_PATH, encoding="utf-8") as policy_file:
                policy = policy_file.read()
        else:
            # Write this container group to an ARM template file
            # Don't remove it unless policy gen worked
            tmp_arm_template_path = tempfile.mktemp(suffix=".json")
            with open(tmp_arm_template_path, "w", encoding="utf-8") as file:
                json.dump({"resources": [container_group]}, file, indent=2)

            print("Calling acipolicygen and saving policy to file")
            subprocess.run(["az", "extension", "add", "--name", "confcom", "--yes"], check=True)
            args = [
                "az",
                "confcom",
                "acipolicygen",
                "-a",
                tmp_arm_template_path,
                "--outraw-pretty-print",
                *(["--debug-mode"] if policy_type == "debug" else []),
                *(["--include-fragments", "--fragments-json", fragments_json] if fragments_json else []),
                *(["--infrastructure-svn", str(infrastructure_svn)] if infrastructure_svn is not None else []),
            ]
            print("Running: " + " ".join(args), flush=True)
            sys.stderr.flush()
            res = subprocess.run(
                args,
                check=True,
                stdout=subprocess.PIPE,
            )
            policy = res.stdout.decode()
            os.remove(tmp_arm_template_path)

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
