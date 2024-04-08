# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import unittest
import os

from c_aci_testing.target_run import target_run

class ExampleTest(unittest.TestCase):
    def test_example(self):
        
        target_dir = os.path.realpath(os.path.dirname(__file__))
        with target_run(target_dir, "my-deployment") as deployment_id:
            ... # Do something with the deployment

        # Cleanup happens after block has finished


if __name__ == "__main__":
    unittest.main()