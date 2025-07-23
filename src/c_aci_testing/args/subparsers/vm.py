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
from ..parameters.vm import (
    parse_vm_image,
    parse_vm_size,
    parse_vm_win_flavor,
    parse_runc_prefix,
    parse_vm_zones,
    parse_uvm_rootfs,
    parse_uvm_kernel,
    parse_uvm_containerd_shim,
)
from ..parameters.storage_account import parse_storage_account
from ..parameters.resource_tags import parse_resource_tags


def subparse_vm(vm: argparse.ArgumentParser):

    vm_subparser = vm.add_subparsers(dest="vm_command", required=True)

    create = vm_subparser.add_parser("create")
    parse_deployment_name(create)
    parse_subscription(create)
    parse_resource_group(create)
    parse_location(create)
    parse_managed_identity(create)
    parse_cplat_args(create)
    parse_storage_account(create)
    parse_vm_image(create)
    parse_vm_size(create)
    parse_vm_zones(create)
    parse_resource_tags(create)
    parse_uvm_rootfs(create)
    parse_uvm_kernel(create)
    parse_uvm_containerd_shim(create)

    create_noinit = vm_subparser.add_parser("create_noinit")
    parse_deployment_name(create_noinit)
    parse_subscription(create_noinit)
    parse_resource_group(create_noinit)
    parse_location(create_noinit)
    parse_managed_identity(create_noinit)
    parse_vm_image(create_noinit)
    parse_vm_size(create_noinit)
    parse_vm_zones(create_noinit)
    parse_resource_tags(create_noinit)

    generate_scripts = vm_subparser.add_parser("generate_scripts")
    parse_target_path(generate_scripts)
    generate_scripts.add_argument("output_dir", type=str)
    parse_subscription(generate_scripts)
    parse_resource_group(generate_scripts)
    parse_vm_win_flavor(generate_scripts)
    parse_registry(generate_scripts)
    parse_repository(generate_scripts)
    parse_tag(generate_scripts)
    parse_runc_prefix(generate_scripts)

    runc = vm_subparser.add_parser("runc")
    parse_target_path(runc)
    parse_deployment_name(runc)
    parse_subscription(runc)
    parse_resource_group(runc)
    parse_storage_account(runc)
    parse_vm_win_flavor(runc)
    parse_registry(runc)
    parse_repository(runc)
    parse_tag(runc)
    parse_runc_prefix(runc)

    check = vm_subparser.add_parser("check")
    parse_deployment_name(check)
    parse_subscription(check)
    parse_resource_group(check)
    parse_runc_prefix(check)

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
    parse_storage_account(deploy)
    parse_vm_image(deploy)
    parse_runc_prefix(deploy)
    parse_vm_size(deploy)
    parse_vm_win_flavor(deploy)
    parse_vm_zones(deploy)
    parse_resource_tags(deploy)

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

    cp_into = vm_subparser.add_parser("cp_into")
    cp_into.add_argument("src", type=str)
    cp_into.add_argument("dst", type=str)
    cp_into.add_argument("run_command", type=str, nargs="?", default="")
    parse_deployment_name(cp_into)
    parse_subscription(cp_into)
    parse_resource_group(cp_into)
    parse_storage_account(cp_into)

    exec = vm_subparser.add_parser("exec")
    parse_deployment_name(exec)
    parse_subscription(exec)
    parse_resource_group(exec)
    exec.add_argument("cmd", type=str)

    cat = vm_subparser.add_parser("cat")
    cat.add_argument("file_path", type=str)
    parse_deployment_name(cat)
    parse_subscription(cat)
    parse_resource_group(cat)
    parse_storage_account(cat)

    cache_cplat = vm_subparser.add_parser("cache_cplat")
    parse_cplat_args(cache_cplat)
    parse_storage_account(cache_cplat)
