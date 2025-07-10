#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import os

from argparse import ArgumentParser


def parse_vm_image(parser: ArgumentParser):
    parser.add_argument(
        "--use-official-images",
        action="store_true",
        default=os.getenv("USE_OFFICIAL_IMAGES", "").lower() == "true",
        help="Use the official image for the VM",
    )

    parser.add_argument(
        "--vm-image",
        type=str,
        default=os.getenv("VM_IMAGE", ""),
        help="The image to use for the VM",
    )

    parser.add_argument(
        "--official-image-sku",
        type=str,
        default=os.getenv("OFFICIAL_IMAGE_SKU", ""),
        help="The SKU for the official image",
    )

    parser.add_argument(
        "--official-image-version",
        type=str,
        default=os.getenv("OFFICIAL_IMAGE_VERSION", ""),
        help="The version for the official image",
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


def parse_runc_prefix(parser: ArgumentParser):
    parser.add_argument(
        "--prefix",
        type=str,
        default=os.getenv("RUNC_PREFIX", "lcow"),
    )


def parse_vm_zones(parser: ArgumentParser):
    parser.add_argument(
        "--zone",
        type=str,
        default=os.getenv("VM_ZONE", ""),
        dest="vm_zone",
        help="The zone to use for the VM, or empty",
    )

def parse_uvm_rootfs(parser: ArgumentParser):
    parser.add_argument(
        "--uvm-rootfs",
        type=lambda x: os.path.abspath(x) if x else "",
        default=os.getenv("UMV_ROOTFS", ""),
        help="A path to a custom rootfs for the UVM (Leave empty to use default)",
    )


def parse_uvm_kernel(parser: ArgumentParser):
    parser.add_argument(
        "--uvm-kernel",
        type=lambda x: os.path.abspath(x) if x else "",
        default=os.getenv("UMV_KERNEL", ""),
        help="A path to a custom kernel for the UVM (Leave empty to use default)",
    )
