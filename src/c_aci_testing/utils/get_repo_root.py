#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations

import subprocess


def get_repo_root(path: str) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=path,
    ).strip().decode()
