#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import os


def parse_storage_account(parser, allow_empty: bool = False):
    parser.add_argument(
        "--storage-account", type=str, default=os.getenv("STORAGE_ACCOUNT", "" if allow_empty else None)
    )
