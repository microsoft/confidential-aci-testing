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

WCOW_ALLOW_ALL_POLICY_REGO_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "templates",
    "wcow_allow_all_policy.rego",
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

    arm_template_json = parse_bicep(
        target_path, subscription, resource_group, deployment_name, registry, repository, tag
    )

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

        # Detect osType per CG: confidential WCOW needs a different policy
        # shape (api_version 0.11.0, mount_cims rule, env_list field on
        # create_container/exec_in_container/exec_external) than confidential
        # LCOW.
        #
        # For policy_type == "allow_all" we use a per-osType static rego
        # template (the only fully-permissive case; confcom always emits
        # strict policies bound to container layers).
        #
        # For policy_type in ("generated", "debug") we delegate to
        # `az confcom acipolicygen`. The devrelease confcom 1.3.0+wcow
        # auto-detects the per-CG osType from the ARM template and emits
        # the correct LCOW or WCOW shape. Upstream stable confcom is
        # LCOW-only at the time of writing; if a confidential WCOW CG is
        # passed through stable confcom, it will produce an LCOW-shaped
        # policy that the WCOW enforcer rejects at runtime.
        os_type = container_group["properties"].get("osType", "Linux")
        is_wcow = isinstance(os_type, str) and os_type.lower() == "windows"

        if policy_type == "allow_all":
            policy_path = WCOW_ALLOW_ALL_POLICY_REGO_PATH if is_wcow else ALLOW_ALL_POLICY_REGO_PATH
            with open(policy_path, encoding="utf-8") as policy_file:
                policy = policy_file.read()
        else:
            # Write this container group to an ARM template file.
            # Clear any pre-populated ccePolicy first: confcom's rego parser
            # can choke on existing WCOW-shape policy text it's about to
            # overwrite anyway.
            cg_for_confcom = json.loads(json.dumps(container_group))
            ccp = cg_for_confcom.get("properties", {}).get("confidentialComputeProperties")
            if isinstance(ccp, dict) and "ccePolicy" in ccp:
                ccp["ccePolicy"] = ""
            # Don't remove it unless policy gen worked
            tmp_arm_template_path = tempfile.mktemp(suffix=".json")
            with open(tmp_arm_template_path, "w", encoding="utf-8") as file:
                json.dump({"resources": [cg_for_confcom]}, file, indent=2)

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
        parameters={
            "ccePolicies": "{\n"
            + "\n".join([f"  {group_id}: '{policy}'" for group_id, policy in policies.items()])
            + "\n}"
        },
    )
