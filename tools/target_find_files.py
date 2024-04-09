#!/usr/bin/env python3

# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os

def find_bicep_file(directory):
    for bicep_file in os.listdir(directory):
        if bicep_file.endswith(".bicep"):
            return bicep_file

def find_bicep_param_file(directory):
    for bicep_file in os.listdir(directory):
        if bicep_file.endswith(".bicepparam"):
            return bicep_file