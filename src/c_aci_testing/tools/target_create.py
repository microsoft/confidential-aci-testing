#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations

import os
import subprocess


def target_create(
    target_path: str,
    name: str,
    **kwargs,
):
    # Ensure the target path is an empty directory
    os.makedirs(target_path, exist_ok=True)
    if os.listdir(target_path):
        print("Target directory path must be empty")
        return

    # Copy the template files to the target path
    template_path = os.path.join(os.path.dirname(__file__), "..", "templates", "target")
    subprocess.run(["cp", "-r", template_path + "/.", target_path], check=True)

    if name != "example":
        for file_path in os.listdir(target_path):

            # Rename files to match target name
            old_file_path = os.path.join(target_path, file_path)
            new_file_path = os.path.join(target_path, file_path.replace("example", name.replace("-", "_")))
            if "example" in file_path:
                subprocess.run(["mv", old_file_path, new_file_path], check=True)

            # Replace "example" with target name in file contents
            with open(new_file_path) as f:
                file_contents = f.read()
            with open(new_file_path, "w") as f:
                f.write(file_contents.replace("example", name.replace("-", "_")))
