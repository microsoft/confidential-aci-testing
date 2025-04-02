#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

from argparse import ArgumentParser
from .. import extend_dict


def parse_resource_tags(parser: ArgumentParser):
    extend_dict.register(parser)

    parser.add_argument(
        "--resource-tags",
        nargs="*",
        action="extend_dict",
        help="ARM Tags to set on the VM resource. Syntax: key=value. Can be specified multiple times.",
    )
