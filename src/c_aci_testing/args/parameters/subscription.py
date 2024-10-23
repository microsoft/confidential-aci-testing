#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import os
import subprocess


def parse_subscription(parser):

    parser.add_argument(
        "--subscription",
        help="The Azure subcription ID to use",
        type=str,
        default=os.getenv(
            "SUBSCRIPTION",
            subprocess.run(
                ["az", "account", "show", "--query", "id", "--output", "tsv"],
                stdout=subprocess.PIPE,
                check=True,
            )
            .stdout.decode()
            .rstrip(os.linesep),
        ),
    )
