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
from ..parameters.yaml_path import parse_yaml_path
from ..parameters.policy_type import parse_policy_type
from ..parameters.fragments_json import parse_fragments_json
from ..parameters.infrastructure_svn import parse_infrastructure_svn
from ..parameters.follow import parse_follow
from ..parameters.monitor_duration_secs import parse_monitor_duration_secs
from ..parameters.deploy_output_file import parse_deploy_output_file
from ..parameters.no_cleanup import parse_no_cleanup
from ..parameters.prefer_pull import parse_prefer_pull
from ..parameters.replicas import parse_replicas


def subparse_vn2(vm: argparse.ArgumentParser):

    vn2_subparser = vm.add_subparsers(dest="vn2_command", required=True)

    generate_yaml = vn2_subparser.add_parser("generate_yaml")
    parse_deployment_name(generate_yaml)
    parse_managed_identity(generate_yaml)
    parse_target_path(generate_yaml)
    parse_subscription(generate_yaml)
    parse_resource_group(generate_yaml)
    parse_registry(generate_yaml)
    parse_repository(generate_yaml)
    parse_tag(generate_yaml)
    parse_yaml_path(generate_yaml)
    parse_replicas(generate_yaml)

    # Deploy command
    deploy = vn2_subparser.add_parser("deploy")
    parse_target_path(deploy)
    parse_yaml_path(deploy)
    parse_monitor_duration_secs(deploy)
    parse_deploy_output_file(deploy)

    # Logs command
    logs = vn2_subparser.add_parser("logs")
    parse_deployment_name(logs)
    parse_follow(logs)

    # Remove command
    remove = vn2_subparser.add_parser("remove")
    parse_deployment_name(remove)

    # Policygen command
    policygen = vn2_subparser.add_parser("policygen")
    parse_target_path(policygen)
    parse_yaml_path(policygen)
    parse_policy_type(policygen)
    parse_fragments_json(policygen)
    parse_infrastructure_svn(policygen)

    # Get-ip command
    get_ip = vn2_subparser.add_parser("get-ip")
    parse_deployment_name(get_ip)
    get_ip.add_argument(
        "--timeout",
        type=int,
        help="Timeout in seconds to wait for the service to be ready",
        default=300,
    )

    create_pull_secret = vn2_subparser.add_parser("create_pull_secret")
    parse_registry(create_pull_secret)

    target = vn2_subparser.add_parser("target")
    target_subparser = target.add_subparsers(dest="target_command", required=True)

    run = target_subparser.add_parser("run")
    parse_target_path(run)
    parse_deployment_name(run)
    parse_subscription(run)
    parse_resource_group(run)
    parse_registry(run)
    parse_repository(run)
    parse_tag(run)
    parse_managed_identity(run)
    parse_policy_type(run)
    parse_follow(run)
    parse_prefer_pull(run)
    parse_replicas(run)
    parse_monitor_duration_secs(run)
