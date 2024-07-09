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
from ..utils.get_target_name import get_target_name


def target_add_test(
    target_path: str,
    **kwargs,
):
    # Copy the python runner code to the target
    test_path = os.path.join(target_path, "test.py")
    shutil.copy(
        os.path.join(os.path.dirname(__file__), "..", "templates", "target_python_test.py"),
        test_path,
    )

    # Find replace example for target name
    target_name = get_target_name(target_path)
    title_case_target_name = target_name.title()

    with open(test_path) as f:
        file_contents = f.read()

    with open(test_path, "w") as f:
        f.write(
            file_contents
                .replace("example", target_name.replace("-", "").replace("_", ""))
                .replace("Example", title_case_target_name.replace("-", "").replace("_", ""))
            )

    # If there isn't already a pytest configuration file create one
    vs_code_path = None
    try:
        vs_code_path = os.path.join(get_repo_root(target_path), ".vscode")
    except subprocess.CalledProcessError:
        print("Can't find workspace root, configure manually to continue")

    if vs_code_path is None:
        return

    if not os.path.exists(vs_code_path):
        os.mkdir(vs_code_path)

    template_path = os.path.join(os.path.dirname(__file__), "..", "templates", "vs_code_settings.json")
    settings_path = os.path.join(vs_code_path, "settings.json")

    if not os.path.exists(settings_path):
        shutil.copy(template_path, settings_path)
    else:
        with open(template_path) as f:
            template = json.load(f)
        with open(settings_path) as f:
            settings = json.load(f)

        if any(key in settings for key in template):
            print("Settings file already contains pytest configuration, skipping")
            return

        with open(settings_path, "w") as f:
            json.dump({**settings, **template}, f, indent=4)
