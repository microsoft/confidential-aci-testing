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


def parse_command():

    arg_parser = argparse.ArgumentParser(
        "Utilities for testing workflows involving Confidential ACI."
    )

    subparser = arg_parser.add_subparsers(dest="command", required=True)
    subparser.add_parser("aci")
    subparser.add_parser("env")
    subparser.add_parser("github")
    subparser.add_parser("infra")
    subparser.add_parser("images")
    subparser.add_parser("policies")
    subparser.add_parser("target")
    subparser.add_parser("vscode")

    args, _ = arg_parser.parse_known_args()

    if args.command == "aci":
        subparse_aci(subparser.choices["aci"])
    elif args.command == "env":
        subparse_env(subparser.choices["env"])
    elif args.command == "github":
        subparse_github(subparser.choices["github"])
    elif args.command == "infra":
        subparse_infra(subparser.choices["infra"])
    elif args.command == "images":
        subparse_images(subparser.choices["images"])
    elif args.command == "policies":
        subparse_policies(subparser.choices["policies"])
    elif args.command == "target":
        subparse_target(subparser.choices["target"])
    elif args.command == "vscode":
        subparse_vscode(subparser.choices["vscode"])
    else:
        raise argparse.ArgumentError(None, "command is required")

    args = arg_parser.parse_args()

    missing_args = []
    exceptions = ["repository", "tag"]
    for key, value in vars(args).items():
        if value is None and key not in exceptions:
            missing_args.append(key)

    if missing_args:
        raise argparse.ArgumentError(
            None, os.linesep.join(f"--{key.replace('_', '-')} is required" for key in missing_args)
        )

    return args
