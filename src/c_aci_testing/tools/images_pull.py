#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations

import os
import subprocess
import time


def login_with_retry(registry: str):
    attempts = 0
    max_attempts = 3
    while attempts < max_attempts:
        try:
            subprocess.run(["az", "acr", "login", "--name", registry], check=True)
            return
        except subprocess.CalledProcessError:
            attempts += 1
            if attempts == max_attempts:
                print(f"Failed to login to {registry} after {max_attempts} attempts.")
                raise
            else:
                sleep_s = 2 ** (attempts + 1)
                print(f"Retrying login to {registry} in {sleep_s}s...")
                time.sleep(sleep_s)


def images_pull(
    target_path: str,
    registry: str,
    repository: str | None,
    tag: str | None,
    **kwargs,
) -> list[str]:
    if "." not in registry or registry.endswith(".azurecr.io"):
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
