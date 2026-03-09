#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import os


def parse_timeout(parser):

    parser.add_argument(
        "--timeout",
        help="Timeout in seconds for the deployment to complete. If not specified, wait indefinitely.",
        type=int,
        default=0,
    )
