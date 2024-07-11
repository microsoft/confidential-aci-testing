#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import argparse


def subparse_env(env: argparse.ArgumentParser):

    env_subparser = env.add_subparsers(dest="env_command", required=True)
    env_subparser.add_parser("create")
