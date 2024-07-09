#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import argparse

from ..parameters.target_path import parse_target_path


def subparse_vscode(vscode):

    vscode_subparser = vscode.add_subparsers(dest="vscode_command")
    run_debug = vscode_subparser.add_parser("run_debug")
    parse_target_path(run_debug)
