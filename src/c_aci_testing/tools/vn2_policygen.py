#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys
import os
import yaml
import base64

from c_aci_testing.utils.find_bicep import find_bicep_files

ALLOW_ALL_POLICY_REGO_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "templates",
    "allow_all_policy.rego",
)


def vn2_policygen(
    target_path: str,
    yaml_path: str,
    policy_type: str,
    fragments_json: str | None = None,
    infrastructure_svn: int | None = None,
    **kwargs,
):
    bicep_file_path, _ = find_bicep_files(target_path)
    bicep_file_name = re.sub(r"\.bicep$", "", os.path.basename(bicep_file_path))

    if not yaml_path:
        yaml_path = os.path.join(target_path, f"{bicep_file_name}.yaml")

    rego_output_path = Path(target_path) / f"policy_{bicep_file_name}.rego"

    if policy_type != "allow_all":
        print("Calling acipolicygen and saving policy to file")
        subprocess.run(["az", "extension", "add", "--name", "confcom", "--yes"], check=True)
        args = [
            "az",
            "confcom",
            "acipolicygen",
            "--virtual-node-yaml",
            yaml_path,
            *(["--debug-mode"] if policy_type == "debug" else []),
            *(["--include-fragments", "--fragments-json", fragments_json] if fragments_json else []),
            *(["--infrastructure-svn", str(infrastructure_svn)] if infrastructure_svn is not None else []),
            "--outraw-pretty-print",
        ]
        print("Running: " + " ".join(args), flush=True)
        sys.stderr.flush()
        res = subprocess.run(
            args,
            check=True,
            stdout=subprocess.PIPE,
        )
        policy = res.stdout.decode()
    else:
        with open(ALLOW_ALL_POLICY_REGO_PATH, encoding="utf-8") as policy_file:
            policy = policy_file.read()
    with open(rego_output_path, "wt") as f:
        f.write(policy)
    print(f"Policy written to {rego_output_path}")

    with open(yaml_path, "rt") as f:
        yaml_data = list(yaml.safe_load_all(f))
        for r in yaml_data:
            try:
                if r["kind"] == "Deployment":
                    r["spec"]["template"]["metadata"]["annotations"][
                        "microsoft.containerinstance.virtualnode.ccepolicy"
                    ] = base64.b64encode(policy.encode("utf8")).decode("utf8")
            except KeyError:
                continue
        with open(yaml_path, "wt") as f:
            yaml.dump_all(yaml_data, f)
