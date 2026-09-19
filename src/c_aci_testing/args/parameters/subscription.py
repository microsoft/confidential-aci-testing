#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import os
import subprocess


def parse_subscription(parser):
    
    def get_default_subscription():
        """Get default subscription, with fallback if Azure CLI fails."""
        env_value = os.getenv("SUBSCRIPTION")
        if env_value:
            return env_value
        
        try:
            result = subprocess.run(
                ["az", "account", "show", "--query", "id", "--output", "tsv"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            return result.stdout.decode().rstrip(os.linesep)
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Return None if Azure CLI is not available or user not logged in
            return None

    parser.add_argument(
        "--subscription",
        help="The Azure subcription ID to use",
        type=str,
        default=get_default_subscription(),
    )
