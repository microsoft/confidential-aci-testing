#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations

import os


def parse_fragment_json(parser):

    parser.add_argument(
        "--fragment-json",
        help="Optional path to JSON file containing fragment information to use for generating a policy.",
        type=os.path.abspath,
        default=None,
    )
