#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import os


def parse_target_path(parser):
    parser.add_argument(
        "target_path",
        help="The relative path to the c-aci-testing target directory",
        type=os.path.abspath,
        default=os.getcwd(),
    )
