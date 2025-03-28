#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

import subprocess
import json
import time

azurecr_io_suffix = ".azurecr.io"


def strip_acr_suffix(registry: str) -> str | None:
    """
    Strips the ".azurecr.io" suffix from the registry name if present, or return None if this is not an ACR registry.
    """

    if "." in registry and not registry.endswith(azurecr_io_suffix):
        return None

    if registry.endswith(azurecr_io_suffix):
        return registry[: -len(azurecr_io_suffix)]

    return registry


def get_acr_token(registry: str) -> str:
    registry_name = strip_acr_suffix(registry)
    if not registry_name:
        raise ValueError("Registry is not ACR")

    tries = 0
    while tries < 5:
        try:
            res = subprocess.run(
                ["az", "acr", "login", "-n", registry_name, "--expose-token"],
                stdout=subprocess.PIPE,
                check=True,
            )
            return json.loads(res.stdout)["accessToken"]
        except subprocess.CalledProcessError:
            tries += 1
            time.sleep(1)
    raise Exception("Failed to get ACR token in 5 tries")


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
