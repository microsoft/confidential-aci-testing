#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import os
import tempfile

from c_aci_testing.tools.aci_param_set import aci_param_set


def test_aci_param_set_dict():
    """Test aci_param_set with dictionary parameters."""
    with tempfile.TemporaryDirectory() as test_dir:
        # Create minimal test bicep files
        with open(os.path.join(test_dir, "main.bicep"), "w") as f:
            f.write("param location string = 'eastus'\n")
        
        with open(os.path.join(test_dir, "main.bicepparam"), "w") as f:
            f.write("param location='eastus'\n")
        
        # Test with dictionary
        aci_param_set(
            test_dir,
            parameters={"location": "westus"},
        )
        
        # Verify the parameter was updated
        with open(os.path.join(test_dir, "main.bicepparam"), "r") as f:
            content = f.read()
            assert "param location='westus'" in content
            

def test_aci_param_set_list():
    """Test aci_param_set with list parameters."""
    with tempfile.TemporaryDirectory() as test_dir:
        # Create minimal test bicep files
        with open(os.path.join(test_dir, "main.bicep"), "w") as f:
            f.write("param location string = 'eastus'\n")
        
        with open(os.path.join(test_dir, "main.bicepparam"), "w") as f:
            f.write("param location='eastus'\n")
        
        # Test with list
        parameters_list = ["location=westus2"]
        aci_param_set(
            test_dir,
            parameters=parameters_list,
        )
        
        # Verify the parameter was updated
        with open(os.path.join(test_dir, "main.bicepparam"), "r") as f:
            content = f.read()
            assert "param location='westus2'" in content