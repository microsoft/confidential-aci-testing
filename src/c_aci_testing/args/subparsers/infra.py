#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import os

from ..parameters.location import parse_location
from ..parameters.managed_identity import parse_managed_identity
from ..parameters.registry import parse_registry
from ..parameters.resource_group import parse_resource_group
from ..parameters.subscription import parse_subscription


def subparse_infra(infra):

    infra_subparser = infra.add_subparsers(dest="infra_command")
    deploy = infra_subparser.add_parser("deploy")

    parse_subscription(deploy)
    parse_resource_group(deploy)
    parse_registry(deploy)
    parse_managed_identity(deploy)
    parse_location(deploy)

    deploy.add_argument(
        "--github-repo",
        help="The Github repository to give credentials for",
        type=str,
        default=os.getenv("GITHUB_REPO"),
    )
