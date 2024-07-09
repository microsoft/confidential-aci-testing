#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations

import os
import subprocess


def images_build(
    target_path: str,
    registry: str,
    repository: str | None,
    tag: str | None,
    services=None,
    **kwargs,
):
    if services is None:
        services = []

    build_command = ["docker-compose", "build"]
    for service in services:
        build_command.append(service)

    print(f"Building images for {registry}")
    subprocess.run(["docker", "image", "list"])
    subprocess.run(
        build_command,
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
    subprocess.run(["docker", "image", "list"])

    print("Built all images successfully")
