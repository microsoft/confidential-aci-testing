#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations

import os
import shutil
import subprocess

from ..utils.get_repo_root import get_repo_root
from ..utils.get_target_name import get_target_name


def github_workflow(
    target_path: str,
    **kwargs,
):
    repo_root = None
    try:
        repo_root = get_repo_root(target_path)
    except subprocess.CalledProcessError:
        print("Can't find workspace root, configure manually to continue")

    if repo_root is None:
        return

    github_path = os.path.join(repo_root, ".github")
    if not os.path.exists(github_path):
        os.mkdir(github_path)
    workflows_path = os.path.join(github_path, "workflows")
    if not os.path.exists(workflows_path):
        os.mkdir(workflows_path)

    template_path = os.path.join(os.path.dirname(__file__), "..", "templates", "github_workflow.yml")
    workflow_path = os.path.join(workflows_path, f"{get_target_name(target_path)}.yml")
    if not os.path.exists(workflow_path):
        shutil.copy(template_path, workflow_path)
    else:
        print(f"Workflow file for {get_target_name(target_path)} already exists, skipping")

    # Find replace example for target name
    target_name = get_target_name(target_path)
    title_case_target_name = target_name.title()

    with open(workflow_path) as f:
        file_contents = f.read()

    with open(workflow_path, "w") as f:
        f.write(
            file_contents
            .replace("example", target_name.replace("-", "").replace("_", ""))
            .replace("Example", title_case_target_name.replace("-", "").replace("_", ""))
            .replace("<TARGET_PATH>", os.path.relpath(target_path, repo_root))
        )
