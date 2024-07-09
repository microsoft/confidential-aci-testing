#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import argparse

from ..parameters.target_path import parse_target_path


def subparse_github(github: argparse.ArgumentParser):

    github_subparser = github.add_subparsers(dest="github_command")
    workflow = github_subparser.add_parser("workflow")
    parse_target_path(workflow)
