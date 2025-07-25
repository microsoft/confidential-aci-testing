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

from c_aci_testing.utils.find_bicep import find_bicep_files


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
    with open(rego_output_path, "wt") as f:
        f.write(policy)
    print(f"Policy written to {rego_output_path}")

    args.pop()  # remove --outraw-pretty-print
    sys.stderr.flush()
    subprocess.run(
        args,
        check=True,
    )
    print(f"Policy applied to {yaml_path}")
