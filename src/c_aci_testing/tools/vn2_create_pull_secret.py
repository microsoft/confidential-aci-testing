#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import subprocess
import sys

from c_aci_testing.utils.acr import get_acr_token, strip_acr_suffix, azurecr_io_suffix


def get_pull_secret_name(registry: str) -> str | None:
    registry_name = strip_acr_suffix(registry)
    if not registry_name:
        return None

    return f"acr-auth-{registry_name}"


def vn2_create_pull_secret(registry: str, **kwargs):
    """
    Creates a short-lived token and use it as a pull secret for the given ACR.
    """

    registry_name = strip_acr_suffix(registry)
    if not registry_name:
        print(f"Skipping pull secret creation for {registry} as it is not an ACR.")
        return

    registry = f"{registry_name}{azurecr_io_suffix}"
    print(f"Creating pull secret for {registry}...", flush=True)
    username = "00000000-0000-0000-0000-000000000000"
    password = get_acr_token(registry)
    pull_secret_name = get_pull_secret_name(registry)
    assert pull_secret_name

    try:
        subprocess.run(
            ["kubectl", "delete", "secret", pull_secret_name],
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        pass

    try:
        subprocess.run(
            [
                "kubectl",
                "create",
                "secret",
                "docker-registry",
                pull_secret_name,
                f"--docker-server={registry}",
                f"--docker-username={username}",
                f"--docker-password={password}",
            ],
            stdout=subprocess.DEVNULL,
            check=True
        )
    except subprocess.CalledProcessError as e:
        # don't expose the token to console
        print(f"Failed to create pull secret for {registry}", file=sys.stderr, flush=True)
