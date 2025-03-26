#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import argparse

from ..parameters.deployment_name import parse_deployment_name
from ..parameters.managed_identity import parse_managed_identity
from ..parameters.resource_group import parse_resource_group
from ..parameters.subscription import parse_subscription
from ..parameters.target_path import parse_target_path
from ..parameters.registry import parse_registry
from ..parameters.repository import parse_repository
from ..parameters.tag import parse_tag


def subparse_vn2(vm: argparse.ArgumentParser):

    vn2_subparser = vm.add_subparsers(dest="vn2_command", required=True)

    generate_yaml = vn2_subparser.add_parser("generate_yaml")
    parse_deployment_name(generate_yaml)
    parse_managed_identity(generate_yaml)
    parse_target_path(generate_yaml)
    generate_yaml.add_argument("output_yaml_path", type=str)
    parse_subscription(generate_yaml)
    parse_resource_group(generate_yaml)
    parse_registry(generate_yaml)
    parse_repository(generate_yaml)
    parse_tag(generate_yaml)
    generate_yaml.add_argument(
        "--replicas",
        type=int,
        help="Number of replicas in the deployment template",
        default=1,
    )
