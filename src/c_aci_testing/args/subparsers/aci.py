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
from ..parameters.resource_group import parse_resource_group
from ..parameters.subscription import parse_subscription
from ..parameters.target_path import parse_target_path


def subparse_aci(aci: argparse.ArgumentParser):

    aci_subparser = aci.add_subparsers(dest="aci_command", required=True)

    deploy = aci_subparser.add_parser("deploy")
    parse_target_path(deploy)
    parse_deployment_name(deploy)
    parse_subscription(deploy)
    parse_resource_group(deploy)
    parse_location(deploy)
    parse_managed_identity(deploy)

    monitor = aci_subparser.add_parser("monitor")
    parse_deployment_name(monitor)
    parse_subscription(monitor)
    parse_resource_group(monitor)
    parse_follow(monitor)

    remove = aci_subparser.add_parser("remove")
    parse_deployment_name(remove)
    parse_subscription(remove)
    parse_resource_group(remove)

    param_set = aci_subparser.add_parser("param_set")
    parse_target_path(param_set)
    param_set.add_argument(
        "--parameters",
        action="append",
        help="The parameter key value pair to add in the format key=value",
    )
    param_set.add_argument(
        "--no-add",
        dest="add",
        action="store_false",
        help="Do not add the parameter to the list if it isn't already present",
    )

    get = aci_subparser.add_parser("get")
    get_subparser = get.add_subparsers(dest="get_command", required=True)

    get_ids = get_subparser.add_parser("ids")
    parse_deployment_name(get_ids)
    parse_subscription(get_ids)
    parse_resource_group(get_ids)

    get_ips = get_subparser.add_parser("ips")
    parse_deployment_name(get_ips)
    parse_subscription(get_ips)
    parse_resource_group(get_ips)

    get_is_live = get_subparser.add_parser("is_live")
    parse_deployment_name(get_is_live)
    parse_subscription(get_is_live)
    parse_resource_group(get_is_live)
