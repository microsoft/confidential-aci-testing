#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import argparse

from ..parameters.deployment_name import parse_deployment_name
from ..parameters.follow import parse_follow
from ..parameters.location import parse_location
from ..parameters.managed_identity import parse_managed_identity
from ..parameters.policy_type import parse_policy_type
from ..parameters.registry import parse_registry
from ..parameters.repository import parse_repository
from ..parameters.resource_group import parse_resource_group
from ..parameters.subscription import parse_subscription
from ..parameters.tag import parse_tag
from ..parameters.target_path import parse_target_path
from ..parameters.no_cleanup import parse_no_cleanup
from ..parameters.prefer_pull import parse_prefer_pull


def subparse_target(target: argparse.ArgumentParser):

    target_subparser = target.add_subparsers(dest="target_command", required=True)

    create = target_subparser.add_parser("create")
    parse_target_path(create)
    create.add_argument(
        "--name",
        "-n",
        help="The name of the new target",
        type=str,
        default="example",
    )

    add_test = target_subparser.add_parser("add_test")
    parse_target_path(add_test)

    run = target_subparser.add_parser("run")
    parse_target_path(run)
    parse_deployment_name(run)
    parse_subscription(run)
    parse_resource_group(run)
    parse_registry(run)
    parse_repository(run)
    parse_tag(run)
    parse_location(run)
    parse_managed_identity(run)
    parse_policy_type(run)
    parse_follow(run)
    parse_no_cleanup(run)
    parse_prefer_pull(run)
