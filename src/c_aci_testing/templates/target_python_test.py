# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from __future__ import annotations

import argparse
import os
import unittest
import uuid

from c_aci_testing.args.parameters.location import parse_location
from c_aci_testing.args.parameters.managed_identity import \
    parse_managed_identity
from c_aci_testing.args.parameters.registry import parse_registry
from c_aci_testing.args.parameters.repository import parse_repository
from c_aci_testing.args.parameters.resource_group import parse_resource_group
from c_aci_testing.args.parameters.subscription import parse_subscription
from c_aci_testing.args.parameters.tag import parse_tag
from c_aci_testing.tools.aci_get_ips import aci_get_ips
from c_aci_testing.tools.target_run import target_run_ctx


class ExampleTest(unittest.TestCase):
    def test_example(self):

        parser = argparse.ArgumentParser()
        parse_subscription(parser)
        parse_resource_group(parser)
        parse_registry(parser)
        parse_repository(parser)
        parse_tag(parser)
        parse_location(parser)
        parse_managed_identity(parser)
        args = parser.parse_args()

        target_path = os.path.realpath(os.path.dirname(__file__))
        id = str(uuid.uuid4())

        with target_run_ctx(
            target_path=target_path,
            deployment_name=id,
            **vars(args),
        ) as deployment_ids:
            print(f"Executing test body, container group IP: {aci_get_ips(
                ids=deployment_ids[0],
                **vars(args)
            )}")

        # Cleanup happens after block has finished


if __name__ == "__main__":
    unittest.main()
