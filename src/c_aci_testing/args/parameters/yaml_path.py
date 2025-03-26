#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

from argparse import ArgumentParser


def parse_yaml_path(parser: ArgumentParser):
    parser.add_argument(
        "--yaml-path",
        type=str,
        help="Path to the YAML file to generate. Default is workload_name.yaml",
    )
