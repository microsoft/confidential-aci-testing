#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import os


def parse_resource_group(parser):

    parser.add_argument(
        "--resource-group",
        help="The Azure resource group to use",
        type=str,
        default=os.getenv("RESOURCE_GROUP"),
    )
