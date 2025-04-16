#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations

from argparse import Action, Namespace
from typing import Any, Sequence
from argparse import ArgumentParser, ArgumentError


class ExtendDictAction(Action):
    """Custom action to parse key=value pairs from command line arguments."""

    def __call__(
        self,
        parser: ArgumentParser,
        namespace: Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ) -> None:
        kv_pairs = getattr(namespace, self.dest, {})
        if kv_pairs is None:
            kv_pairs = {}
        if isinstance(values, str):
            values = [values]
        if not values:
            return
        for value in values:
            assert isinstance(value, str)
            if "=" not in value:
                raise ArgumentError(self, f"Invalid format for key-value pair: {value}. Expected format is key=value.")
            key, val = value.split("=", 1)
            key = key.strip()
            val = val.strip()
            kv_pairs[key] = val
        setattr(namespace, self.dest, kv_pairs)


def register(parser: ArgumentParser) -> None:
    parser.register("action", "extend_dict", ExtendDictAction)
