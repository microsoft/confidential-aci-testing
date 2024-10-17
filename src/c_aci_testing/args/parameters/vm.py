#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import os

from argparse import ArgumentParser


def parse_vm_image(parser: ArgumentParser):
    parser.add_argument(
        "--vm-image",
        type=str,
        default=os.getenv("VM_IMAGE"),
        help="The image to use for the VM",
    )


def parse_vm_win_flavor(parser: ArgumentParser):
    parser.add_argument(
        "--win-flavor",
        type=str,
        default=os.getenv("WIN_FLAVOR"),
        choices=["ws2022", "ws2025"],
        help="Provide the Windows version for the image",
    )


def parse_vm_size(parser):

    parser.add_argument(
        "--vm-size",
        help="The size of the VM",
        type=str,
        default=os.getenv("VM_SIZE"),
    )
