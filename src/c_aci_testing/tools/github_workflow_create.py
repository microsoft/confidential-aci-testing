#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations

import os
import shutil

from ..utils.get_repo_root import get_repo_root
from ..utils.get_target_name import get_target_name


def vscode_testing(
    target_path: str,
    **kwargs,
):
    github_path = os.path.join(get_repo_root(), ".github")
    if not os.path.exists(github_path):
        os.mkdir(github_path)
    workflows_path = os.path.join(github_path, "workflows")
    if not os.path.exists(workflows_path):
        os.mkdir(workflows_path)

    template_path = os.path.join(os.path.dirname(__file__), "..", "templates", "github_workflow.yml")
    workflow_path = os.path.join(workflows_path, f"{get_target_name(target_path)}.json")
    if not os.path.exists(workflow_path):
        shutil.copy(template_path, workflow_path)
    else:
        print(f"Workflow file for {get_target_name(target_path)} already exists, skipping")
