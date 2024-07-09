#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations

import json
import os
import shutil
import subprocess

from ..utils.get_repo_root import get_repo_root


def vscode_run_debug(
    target_path: str,
    **kwargs,
):
    vs_code_path = None
    try:
        vs_code_path = os.path.join(get_repo_root(target_path), ".vscode")
    except subprocess.CalledProcessError:
        print("Can't find workspace root, configure manually to continue")

    if vs_code_path is None:
        return

    if not os.path.exists(vs_code_path):
        os.mkdir(vs_code_path)

    template_path = os.path.join(os.path.dirname(__file__), "..", "templates", "vs_code_run_debug.json")
    launch_path = os.path.join(vs_code_path, "launch.json")
    if not os.path.exists(launch_path):
        print(f"Copying template to {launch_path}")
        shutil.copy(template_path, launch_path)
    else:
        print(f"Merging template into {launch_path}")
        with open(template_path) as f:
            template = json.load(f)
        with open(launch_path) as f:
            launch = json.load(f)

        for config in template["configurations"]:
            if config not in launch["configurations"]:
                launch["configurations"].append(config)

        with open(launch_path, "w") as f:
            json.dump(launch, f, indent=4)
