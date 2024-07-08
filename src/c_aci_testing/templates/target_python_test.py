# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from __future__ import annotations

import os
import unittest
import uuid

from c_aci_testing.tools.aci_get_ips import aci_get_ips
from c_aci_testing.tools.target_run import target_run_ctx


class ExampleTest(unittest.TestCase):
    def test_example(self):

        target_dir = os.path.realpath(os.path.dirname(__file__))
        id = str(uuid.uuid4())

        with target_run_ctx(
            target=target_dir,
            name=f"example-{id}",
            tag=id,
            follow=True
        ) as deployment_ids:
            print(f"Executing test body, container group IP: {aci_get_ips(ids=deployment_ids[0])}")

        # Cleanup happens after block has finished


if __name__ == "__main__":
    unittest.main()
