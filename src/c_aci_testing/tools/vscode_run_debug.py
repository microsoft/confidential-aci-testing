#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations

import json
import os
import shutil

from ..utils.get_repo_root import get_repo_root


def vscode_testing(
    target_path: str,
    **kwargs,
):
    vs_code_path = os.path.join(get_repo_root(), ".vscode")
    if not os.path.exists(vs_code_path):
        os.mkdir(vs_code_path)

    template_path = os.path.join(os.path.dirname(__file__), "..", "templates", "vs_code_run_debug.json")
    launch_path = os.path.join(vs_code_path, "launch.json")
    if not os.path.exists(launch_path):
        shutil.copy(template_path, launch_path)
    else:
        with open(template_path) as f:
            template = json.load(f)
        with open(launch_path) as f:
            launch = json.load(f)

        for config in template["configurations"]:
            if config not in launch["configurations"]:
                launch["configurations"].append(config)
