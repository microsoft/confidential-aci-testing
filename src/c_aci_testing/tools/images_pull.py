#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations

import os
import subprocess

from c_aci_testing.utils.acr import login_with_retry, strip_acr_suffix


def images_pull(
    target_path: str,
    registry: str,
    repository: str | None,
    tag: str | None,
    **kwargs,
) -> list[str]:
    if strip_acr_suffix(registry):  # function returns None if not ACR
        login_with_retry(registry)

    print(f"Pulling images for {registry}")
    for stderr_val in (None, subprocess.PIPE):
        result = subprocess.run(
            ["docker", "compose", "pull"],
            env={
                **os.environ,
                "TARGET": target_path,
                "REGISTRY": registry,
                **({"REPOSITORY": repository} if repository else {}),
                **({"TAG": tag} if tag else {}),
            },
            cwd=target_path,
            check=False,
            stderr=stderr_val,
        )

    images_not_pulled = []
    for line in result.stderr.decode().split(os.linesep):
        if line.strip().startswith("docker compose build"):
            images_not_pulled.extend(line.split()[3:])

    if images_not_pulled:
        print(f'Pulled all images except: {" ".join(images_not_pulled)}')
    else:
        print("Pulled all images successfully")

    return images_not_pulled
