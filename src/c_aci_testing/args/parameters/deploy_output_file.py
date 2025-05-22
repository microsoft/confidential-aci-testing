#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import os


def parse_deploy_output_file(parser):

    parser.add_argument(
        "--deploy-output-file",
        help="Optional output path for deployment information (currently for vn2 only)",
        type=str,
        default=os.getenv("DEPLOY_OUTPUT_FILE", ""),
    )
