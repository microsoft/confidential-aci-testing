#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import os


def parse_vm_size(parser):

    parser.add_argument(
        "--vm-size",
        help="The size of the VM",
        type=str,
        default=os.getenv("VM_SIZE"),
    )
