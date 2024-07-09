#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import os


def parse_registry(parser):

    parser.add_argument(
        "--registry",
        help="The Azure container registry to use",
        type=str,
        default=os.getenv("REGISTRY"),
    )
