#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import os


def parse_managed_identity(parser):

    parser.add_argument(
        "--managed-identity",
        help="The managed identity of the Azure deployment",
        type=str,
        default=os.getenv("MANAGED_IDENTITY"),
    )
