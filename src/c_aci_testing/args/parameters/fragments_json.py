#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations

import os

from argparse import ArgumentParser, FileType


def parse_fragments_json(parser: ArgumentParser):

    parser.add_argument(
        "--fragments-json",
        help="Optional path to JSON file containing fragment information to use for generating a policy.",
        # type=FileType("r"),
        type=str,
        default="",  # this is needed because of some incorrect checks elsewhere
        nargs="?",
    )
