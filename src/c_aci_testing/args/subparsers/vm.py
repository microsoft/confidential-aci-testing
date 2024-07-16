#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import argparse
import os

from ..parameters.deployment_name import parse_deployment_name

from ..parameters.location import parse_location
from ..parameters.managed_identity import parse_managed_identity
from ..parameters.resource_group import parse_resource_group
from ..parameters.subscription import parse_subscription
from ..parameters.target_path import parse_target_path


def subparse_vm(vm: argparse.ArgumentParser):

    vm_subparser = vm.add_subparsers(dest="vm_command", required=True)

    deploy = vm_subparser.add_parser("deploy")
    parse_target_path(deploy)
    parse_deployment_name(deploy)
    parse_subscription(deploy)
    parse_resource_group(deploy)
    parse_location(deploy)
    parse_managed_identity(deploy)
    deploy.add_argument(
        "--vm-image",
        type=str,
        default=os.getenv("VM_IMAGE"),
        help="The image to use for the VM",
    )

    remove = vm_subparser.add_parser("remove")
    parse_deployment_name(remove)
    parse_subscription(remove)
    parse_resource_group(remove)

    get = vm_subparser.add_parser("get")
    get_subparser = get.add_subparsers(dest="get_command", required=True)

    get_ids = get_subparser.add_parser("ids")
    parse_deployment_name(get_ids)
    parse_subscription(get_ids)
    parse_resource_group(get_ids)
