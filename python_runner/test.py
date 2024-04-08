# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import unittest
import os

from c_aci_testing.target_run import target_run, aci_get_ips

class ExampleTest(unittest.TestCase):
    def test_example(self):
        
        target_dir = os.path.realpath(os.path.dirname(__file__))
        with target_run(target_dir, "my-deployment") as deployment_id:
            print(f"Executing test body, container group IP: {aci_get_ips(ids=deployment_id)}")

        # Cleanup happens after block has finished


if __name__ == "__main__":
    unittest.main()