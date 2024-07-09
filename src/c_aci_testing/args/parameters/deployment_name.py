#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import os


def parse_deployment_name(parser):

    parser.add_argument(
        "--deployment-name",
        help="The name of the Azure deployment",
        type=str,
        default=os.getenv("DEPLOYMENT_NAME"),
    )
