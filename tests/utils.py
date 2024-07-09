#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import os


def set_env():
    env_path = os.path.join(os.path.dirname(__file__), "..", "cacitesting.env")
    with open(env_path) as env_file:
        for line in env_file:
            if "=" in line:
                key, value = line.strip().split("=")
                os.environ[key] = value
