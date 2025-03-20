#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations

import os
from argparse import ArgumentParser


def parse_infrastructure_svn(parser: ArgumentParser):
    parser.add_argument(
        "--infrastructure-svn",
        type=int,
        default=os.getenv("INFRASTRUCTURE_SVN", None),
        required=False,
        help="Infra fragment SVN",
    )
