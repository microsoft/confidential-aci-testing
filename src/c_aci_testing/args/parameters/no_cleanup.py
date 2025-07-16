#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations


def parse_no_cleanup(parser):

    parser.add_argument(
        "--no-cleanup",
        dest="cleanup",
        help="Cleanup the target resources after completion",
        action="store_false",
    )
