# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import unittest
import os
import uuid

from c_aci_testing.target_run import target_run_ctx
from c_aci_testing.aci_get_ips import aci_get_ips

class ExampleTest(unittest.TestCase):
    def test_example(self):

        target_dir = os.path.realpath(os.path.dirname(__file__))
        id = str(uuid.uuid4())

        with target_run_ctx(
            target=target_dir,
            name=f"my-deployment-{id}",
            tag=id,
            follow=True
        ) as deployment_id:
            print(f"Executing test body, container group IP: {aci_get_ips(ids=deployment_id)}")

        # Cleanup happens after block has finished


if __name__ == "__main__":
    unittest.main()