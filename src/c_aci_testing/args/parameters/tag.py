#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import os


def parse_tag(parser):

    parser.add_argument(
        "--tag",
        help="The docker image tag to use",
        type=str,
        default=os.getenv("TAG"),
    )
