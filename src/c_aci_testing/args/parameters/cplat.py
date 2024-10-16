#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import os


def parse_cplat_args(parser):
  parser.add_argument(
    "--cplat-feed",
    type=str,
    default=os.getenv("CPLAT_FEED", ""),
  )
  parser.add_argument(
    "--cplat-name",
    type=str,
    default=os.getenv("CPLAT_NAME", ""),
  )
  parser.add_argument(
    "--cplat-version",
    type=str,
    default=os.getenv("CPLAT_VERSION", ""),
  )
  parser.add_argument(
    "--cplat-blob-name",
    type=str,
    default=os.getenv("CPLAT_BLOB_NAME", ""),
  )
