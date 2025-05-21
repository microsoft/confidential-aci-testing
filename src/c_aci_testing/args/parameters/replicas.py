#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations


def parse_replicas(parser):

    parser.add_argument(
        "--replicas",
        type=int,
        help="Number of replicas in the deployment template",
        default=1,
    )
