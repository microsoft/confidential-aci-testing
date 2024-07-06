#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations

import argparse
import os

from .subparsers.aci import subparse_aci
from .subparsers.env import subparse_env
from .subparsers.github import subparse_github
from .subparsers.images import subparse_images
from .subparsers.infra import subparse_infra
from .subparsers.policies import subparse_policies
from .subparsers.target import subparse_target
from .subparsers.vscode import subparse_vscode


def parse():

    arg_parser = argparse.ArgumentParser()

    subparser = arg_parser.add_subparsers(dest="command")
    subparse_aci(subparser)
    subparse_env(subparser)
    subparse_github(subparser)
    subparse_infra(subparser)
    subparse_images(subparser)
    subparse_policies(subparser)
    subparse_target(subparser)
    subparse_vscode(subparser)

    args = arg_parser.parse_args()

    missing_args = []
    exceptions = ["repository", "tag"]
    for key, value in vars(args).items():
        if value is None and key not in exceptions:
            missing_args.append(key)

    if missing_args:
        raise argparse.ArgumentError(None, os.linesep.join(f"--{key.replace('_', '-')} is required" for key in missing_args))

    return args
