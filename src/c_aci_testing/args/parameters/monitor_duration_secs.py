#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import os


def parse_monitor_duration_secs(parser):

    parser.add_argument(
        "--monitor-duration-secs",
        help="How long to check continuously that the deployment is stable (currently for vn2 only)",
        type=int,
        default=os.getenv("MONITOR_DURATION_SECS", "0"),
    )
