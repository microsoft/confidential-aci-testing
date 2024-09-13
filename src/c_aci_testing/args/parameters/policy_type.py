#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations

import os


def parse_policy_type(parser):

    parser.add_argument(
        "--policy-type",
        help="The type of policy to use",
        type=str,
        default=os.getenv("POLICY_TYPE", "generated"),
        choices=[
            "allow_all",
            "debug",
            "generated",
            "none",
        ],
    )
