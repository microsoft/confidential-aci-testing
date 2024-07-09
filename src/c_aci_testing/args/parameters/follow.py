#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations


def parse_follow(parser):
    parser.add_argument(
        "--follow",
        action="store_true",
        help="Whether to follow container logs until completion or not",
    )
