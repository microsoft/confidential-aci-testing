#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import os


def parse_repository(parser):

    parser.add_argument(
        "--repository",
        help="The Azure container repository to use",
        type=str,
        default=os.getenv("REPOSITORY"),
    )
