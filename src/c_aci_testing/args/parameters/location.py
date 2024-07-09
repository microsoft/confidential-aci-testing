#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import os


def parse_location(parser):

    parser.add_argument(
        "--location",
        help="The location of the Azure deployment",
        type=str,
        default=os.getenv("LOCATION"),
    )
