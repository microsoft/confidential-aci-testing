#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import argparse

from ..parameters.registry import parse_registry
from ..parameters.repository import parse_repository
from ..parameters.tag import parse_tag
from ..parameters.target_path import parse_target_path


def subparse_images(images: argparse.ArgumentParser):

    images_subparser = images.add_subparsers(dest="images_command")

    build = images_subparser.add_parser("build")
    parse_target_path(build)
    parse_registry(build)
    parse_repository(build)
    parse_tag(build)

    push = images_subparser.add_parser("push")
    parse_target_path(push)
    parse_registry(push)
    parse_repository(push)
    parse_tag(push)

    pull = images_subparser.add_parser("pull")
    parse_target_path(pull)
    parse_registry(pull)
    parse_repository(pull)
    parse_tag(pull)
