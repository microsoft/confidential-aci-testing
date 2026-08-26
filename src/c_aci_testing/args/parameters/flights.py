#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import os


def parse_flights(parser):

    parser.add_argument(
        "--flights",
        help=(
            "Pipe separated ACI flights to merge into the request, e.g. "
            "'cluster-pool.stamp-4'. Sent as the x-ms-aci-merge-flights header, which "
            "requires the deployment to bypass ARM template deployment. Defaults to "
            "the ACI_FLIGHTS environment variable."
        ),
        type=str,
        default=os.getenv("ACI_FLIGHTS", ""),
    )
