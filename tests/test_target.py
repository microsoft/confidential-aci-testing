#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import argparse
import os
import random
import string
import subprocess
import tempfile
import time

from utils import set_env

from c_aci_testing.args.parameters.location import parse_location
from c_aci_testing.args.parameters.managed_identity import \
    parse_managed_identity
from c_aci_testing.args.parameters.registry import parse_registry
from c_aci_testing.args.parameters.repository import parse_repository
from c_aci_testing.args.parameters.resource_group import parse_resource_group
from c_aci_testing.args.parameters.subscription import parse_subscription
from c_aci_testing.args.parameters.tag import parse_tag
from c_aci_testing.tools.aci_deploy import aci_deploy
from c_aci_testing.tools.aci_get_is_live import aci_get_is_live
from c_aci_testing.tools.aci_monitor import aci_monitor
from c_aci_testing.tools.aci_remove import aci_remove
from c_aci_testing.tools.images_build import images_build
from c_aci_testing.tools.images_push import images_push
from c_aci_testing.tools.policies_gen import policies_gen
from c_aci_testing.tools.target_add_test import target_add_test
from c_aci_testing.tools.target_create import target_create
from c_aci_testing.tools.target_run import target_run_ctx


def parse_args():

    parser = argparse.ArgumentParser()
    parse_subscription(parser)
    parse_resource_group(parser)
    parse_registry(parser)
    parse_repository(parser)
    parse_tag(parser)
    parse_location(parser)
    parse_managed_identity(parser)
    return parser.parse_known_args()[0]


def test_target_run(unit_test_mocks: None):
    set_env()
    args = parse_args()

    # Define a temporary directory to use as a target
    with tempfile.TemporaryDirectory(prefix="target_") as target_path:

        # Create the target
        target_name = ''.join(random.choices(string.ascii_lowercase, k=8))
        target_create(target_path=target_path, name=target_name)

        with target_run_ctx(
            target_path=target_path,
            deployment_name=target_name,
            **args,
        ): ...


def test_target_test_runner(unit_test_mocks: None):
    set_env()

    # Define a temporary directory to use as a target
    with tempfile.TemporaryDirectory(prefix="target_") as target_path:

        # Create the target
        target_name = ''.join(random.choices(string.ascii_lowercase, k=8))
        target_create(target_path=target_path, name=target_name)
        target_add_test(target_path=target_path)

        subprocess.run(
            ["python", os.path.join(target_path, "test.py")],
            check=True,
        )


def test_target_run_debug_policy(unit_test_mocks: None):
    set_env()
    args = parse_args()

    # Define a temporary directory to use as a target
    with tempfile.TemporaryDirectory(prefix="target_") as target_path:

        # Create the target
        target_name = ''.join(random.choices(string.ascii_lowercase, k=8))
        target_create(target_path=target_path, name=target_name)

        with target_run_ctx(
            target_path=target_path,
            deployment_name=target_name,
            **args,
            policy_type="debug",
        ): ...


def test_target_run_allow_all_policy(unit_test_mocks: None):
    set_env()
    args = parse_args()

    # Define a temporary directory to use as a target
    with tempfile.TemporaryDirectory(prefix="target_") as target_path:

        # Create the target
        target_name = ''.join(random.choices(string.ascii_lowercase, k=8))
        target_create(target_path=target_path, name=target_name)

        with target_run_ctx(
            target_path=target_path,
            deployment_name=target_name,
            **args,
            policy_type="allow_all",
        ): ...


def test_target_run_no_cleanup(unit_test_mocks: None):
    set_env()
    args = parse_args()

    # Define a temporary directory to use as a target
    with tempfile.TemporaryDirectory(prefix="target_") as target_path:

        # Create the target
        target_name = ''.join(random.choices(string.ascii_lowercase, k=8))
        target_create(target_path=target_path, name=target_name)

        with open(os.path.join(target_path, "primary.Dockerfile"), "w") as f:
            f.write("""
                FROM mcr.microsoft.com/devcontainers/base:jammy
                CMD sleep infinity
                """
            )

        deployment_info = {
            "deployment_name": target_name,
            **args,
        }

        with target_run_ctx(
            target_path=target_path,
            **deployment_info,
            cleanup=False,
            follow=False,
        ) as target_ctx:
            aci_ids = target_ctx

        assert aci_get_is_live(**deployment_info, aci_ids=aci_ids)

        aci_remove(**deployment_info)

        assert not aci_get_is_live(**deployment_info, aci_ids=aci_ids)


def test_target_run_prefer_pull(unit_test_mocks: None):
    set_env()
    args = parse_args()

    # Define a temporary directory to use as a target
    with tempfile.TemporaryDirectory(prefix="target_") as target_path:

        # Create the target
        target_name = ''.join(random.choices(string.ascii_lowercase, k=8))
        target_create(target_path=target_path, name=target_name)

        # Build and push the image
        images_build(target_path=target_path, **args)
        images_push(target_path=target_path, **args)

        # Delete the dockerfile to break building
        os.remove(os.path.join(target_path, "primary.Dockerfile"))

        with target_run_ctx(
            target_path=target_path,
            deployment_name=target_name,
            **args,
            prefer_pull=True,
        ): ...


def test_target_run_steps(unit_test_mocks: None):
    set_env()
    args = parse_args()

    # Define a temporary directory to use as a target
    with tempfile.TemporaryDirectory(prefix="target_") as target_path:

        # Create the target
        target_name = ''.join(random.choices(string.ascii_lowercase, k=8))
        target_create(target_path=target_path, name=target_name)

        images_build(target_path=target_path, **args)
        images_push(target_path=target_path, **args)
        policies_gen(
            target_path=target_path,
            deployment_name=target_name,
            policy_type="generated",
            **args,
        )
        aci_deploy(target_path=target_path, deployment_name=target_name, **args)
        aci_monitor(deployment_name=target_name, **args)
        aci_remove(deployment_name=target_name, **args)
