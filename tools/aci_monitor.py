#!/usr/bin/env python3

# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import argparse
import os

from .logging_window import LoggingWindow

def aci_monitor(subscription, resource_group, name, ids, follow=True):

    assert (name or ids) and not (name and ids), \
        "Either name or ids must be set, but not both"

    with LoggingWindow(
        header=f"\033[33mMonitoring Container {name or ids[0]}\033[0m",
        prefix="\033[33m| \033[0m",
        max_lines=int(os.environ.get("LOG_LINES", 9999)),
    ) as run_subprocess:

        if name:
            run_subprocess([
                "az", "container", "logs",
                *(["--follow"] if follow else []),
                *(["--subscription", subscription] if subscription else []),
                *(["--resource-group", resource_group] if resource_group else []),
                *(["--name", name]),
            ], check=not follow)
        else:
            for id in ids:
                run_subprocess([
                    "az", "container", "logs",
                    *(["--follow"] if follow else []),
                    *(["--subscription", subscription] if subscription else []),
                    *(["--resource-group", resource_group] if resource_group else []),
                    *(["--ids", id]),
                ], check=not follow)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor deployed target resources")

    parser.add_argument("--subscription",
        help="Azure Subscription ID", default=os.environ.get("SUBSCRIPTION"))
    parser.add_argument("--resource-group", '-g',
        help="Azure Resource Group ID", default=os.environ.get("RESOURCE_GROUP"))
    parser.add_argument("--name", "-n", help="Name of deployment")
    parser.add_argument("--ids", help="ID of deployment")

    args = parser.parse_args()

    aci_monitor(
        subscription=args.subscription,
        resource_group=args.resource_group,
        name=args.name,
        ids=args.ids,
    )
