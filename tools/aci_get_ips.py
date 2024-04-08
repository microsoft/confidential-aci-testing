#!/usr/bin/env python3

import argparse
import os
import subprocess

def aci_get_ips(subscription, resource_group, name, ids):

    assert (name or ids) and not (name and ids), \
        "Either name or ids must be set, but not both"

    az_command = [
        "az", "container", "show",
        "--query", "ipAddress.ip",
        "--output", "tsv",
        *(["--subscription", subscription] if subscription else []),
        *(["--resource-group", resource_group] if resource_group else []),
        *(["--name", name] if name else []),
        *(["--ids", ids] if ids else []),
    ]
    subprocess.run(az_command)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor deployed target resources")

    parser.add_argument("--subscription",
        help="Azure Subscription ID", default=os.environ.get("SUBSCRIPTION"))
    parser.add_argument("--resource-group", '-g',
        help="Azure Resource Group ID", default=os.environ.get("RESOURCE_GROUP"))
    parser.add_argument("--name", "-n", help="Name of deployment")
    parser.add_argument("--ids", help="ID of deployment")
    
    args = parser.parse_args()

    aci_get_ips(
        subscription=args.subscription,
        resource_group=args.resource_group,
        name=args.name,
        ids=args.ids,
    )
