#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations

import os
import subprocess


def images_push(
    target_path: str,
    registry: str,
    repository: str | None,
    tag: str | None,
    **kwargs,
):
    subprocess.run(["az", "acr", "login", "--name", registry], check=True)

    print(f"Pushing images for {registry}")
    subprocess.run(
        ["docker-compose", "push"],
        env={
            **os.environ,
            "TARGET": target_path,
            "REGISTRY": registry,
            **({"REPOSITORY": repository} if repository else {}),
            **({"TAG": tag} if tag else {}),
        },
        cwd=target_path,
        check=True,
    )

    print("Pushed all images successfully")
