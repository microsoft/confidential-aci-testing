#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations


def parse_prefer_pull(parser):

    parser.add_argument(
        "--prefer-pull",
        help="Attempt to pull images before building them",
        action="store_true",
    )
