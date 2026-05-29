#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import subprocess

from .vm_get_ids import vm_get_ids


# Hard cap on retry iterations. The previous unbounded loop hung CI workflows
# when a child resource (e.g. a still-running `RunPowerShellScript` on a VM)
# blocked the VM delete: every iteration produced the same failure and the
# loop never terminated. The cap below ensures we always return; downstream
# callers (workflows, scripts) should follow up with `az vm delete
# --force-deletion yes` to clear stuck child resources if needed.
MAX_DELETE_ITERATIONS = 10


def vm_remove(
    deployment_name: str,
    subscription: str,
    resource_group: str,
    **kwargs,
):
    remaining_resources = set(vm_get_ids(deployment_name, subscription, resource_group))

    if not remaining_resources:
        print(f"Failed to get deployment output. Using default VM name: {deployment_name}-vm")
        remaining_resources = {
            f"/subscriptions/{subscription}/resourceGroups/{resource_group}/providers/Microsoft.Compute/virtualMachines/{deployment_name}-vm"
        }

    iteration = 0
    while remaining_resources:
        iteration += 1
        print(f"Deleting {len(remaining_resources)} resources (attempt {iteration}/{MAX_DELETE_ITERATIONS})...")

        res = subprocess.run(
            [
                "az",
                "resource",
                "delete",
                "--subscription",
                subscription,
                "--resource-group",
                resource_group,
                "--ids",
                *remaining_resources,
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if res.returncode != 0:
            print(f"Failed to delete some resources: {res.stderr.decode()}")

        deleted_resources = set()
        for res_id in remaining_resources:
            res_name = res_id.split("/")[-1]
            res = subprocess.run(
                [
                    "az",
                    "resource",
                    "show",
                    "--ids",
                    res_id,
                ],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            if res.returncode != 0:
                deleted_resources.add(res_id)
                print(f"Removed resource: {res_name}")

        # Bail if no progress this iteration: something is blocking
        # (e.g. a stuck child run-command resource on a VM). Caller should
        # follow up with `az vm delete --force-deletion yes`.
        if not deleted_resources:
            print(
                f"No progress on iteration {iteration}; bailing with "
                f"{len(remaining_resources)} undeletable resource(s):"
            )
            for res_id in sorted(remaining_resources):
                print(f"  {res_id.split('/')[-1]} ({res_id})")
            return

        remaining_resources -= deleted_resources

        if iteration >= MAX_DELETE_ITERATIONS and remaining_resources:
            print(
                f"Hit max iterations ({MAX_DELETE_ITERATIONS}); bailing with "
                f"{len(remaining_resources)} remaining resource(s):"
            )
            for res_id in sorted(remaining_resources):
                print(f"  {res_id.split('/')[-1]} ({res_id})")
            return
