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
from ..parameters.registry import parse_registry
from ..parameters.repository import parse_repository
from ..parameters.tag import parse_tag
from ..parameters.cplat import parse_cplat_args
from ..parameters.vm_size import parse_vm_size


def subparse_vm(vm: argparse.ArgumentParser):

    vm_subparser = vm.add_subparsers(dest="vm_command", required=True)

    create = vm_subparser.add_parser("create")
    parse_deployment_name(create)
    parse_subscription(create)
    parse_resource_group(create)
    parse_location(create)
    parse_managed_identity(create)
    parse_cplat_args(create)
    create.add_argument(
        "--vm-image",
        type=str,
        default=os.getenv("VM_IMAGE"),
        help="The image to use for the VM",
    )
    parse_vm_size(create)

    runc = vm_subparser.add_parser("runc")
    parse_target_path(runc)
    parse_deployment_name(runc)
    parse_subscription(runc)
    parse_resource_group(runc)
    parse_managed_identity(runc)
    parse_registry(runc)
    parse_repository(runc)
    parse_tag(runc)
    runc.add_argument(
        "--lcow-dir-name",
        type=str,
        default=os.getenv("LCOW_DIR_NAME", "lcow"),
    )

    check = vm_subparser.add_parser("check")
    parse_deployment_name(check)
    parse_subscription(check)
    parse_resource_group(check)
    check.add_argument(
        "--lcow-dir-name",
        type=str,
        default=os.getenv("LCOW_DIR_NAME", "lcow"),
    )

    deploy = vm_subparser.add_parser("deploy")
    parse_target_path(deploy)
    parse_deployment_name(deploy)
    parse_subscription(deploy)
    parse_resource_group(deploy)
    parse_location(deploy)
    parse_managed_identity(deploy)
    parse_registry(deploy)
    parse_repository(deploy)
    parse_tag(deploy)
    parse_cplat_args(deploy)
    deploy.add_argument(
        "--vm-image",
        type=str,
        default=os.getenv("VM_IMAGE"),
        help="The image to use for the VM",
    )
    deploy.add_argument(
        "--lcow-dir-name",
        type=str,
        default=os.getenv("LCOW_DIR_NAME", "lcow"),
    )
    parse_vm_size(deploy)

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

    run_script = vm_subparser.add_parser("run_script")
    parse_target_path(run_script)
    run_script.add_argument("script_file", type=str)
    parse_deployment_name(run_script)
    parse_subscription(run_script)
    parse_resource_group(run_script)
    parse_managed_identity(run_script)

    exec = vm_subparser.add_parser("exec")
    parse_deployment_name(exec)
    parse_subscription(exec)
    parse_resource_group(exec)
    exec.add_argument("cmd", type=str)
