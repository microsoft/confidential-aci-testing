#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import argparse

from ..parameters.deployment_name import parse_deployment_name
from ..parameters.policy_type import parse_policy_type
from ..parameters.registry import parse_registry
from ..parameters.repository import parse_repository
from ..parameters.resource_group import parse_resource_group
from ..parameters.subscription import parse_subscription
from ..parameters.tag import parse_tag
from ..parameters.target_path import parse_target_path


def subparse_policies(policies: argparse.ArgumentParser):

    policies_subparser = policies.add_subparsers(dest="policies_command")

    gen = policies_subparser.add_parser("gen")
    parse_target_path(gen)
    parse_deployment_name(gen)
    parse_subscription(gen)
    parse_resource_group(gen)
    parse_registry(gen)
    parse_repository(gen)
    parse_tag(gen)
    parse_policy_type(gen)
