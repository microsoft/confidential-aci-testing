#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import json
import os
import subprocess
import tarfile
import tempfile
import uuid
import time

from c_aci_testing.tools.vm_get_ids import vm_get_ids
from c_aci_testing.utils.vm import run_on_vm


def containerplat_cache(
    storage_account: str, container_name: str, blob_name: str, cplat_feed: str, cplat_name: str, cplat_version: str
):
    with tempfile.TemporaryDirectory() as temp_dir:
        subprocess.run(
            [
                "az",
                "artifacts",
                "universal",
                "download",
                "--organization",
                "https://dev.azure.com/msazure/",
                "--project",
                "dcf1de98-e135-4121-8a6c-99b73705f581",
                "--scope",
                "project",
                "--feed",
                cplat_feed,
                "--name",
                cplat_name,
                "--version",
                cplat_version,
                "--path",
                temp_dir,
            ],
            check=True,
        )

        with open(f"{temp_dir}/deploy.json", "r+", encoding="utf-8") as f:
            data = json.load(f)
            data["Force"] = True
            data["SevSnpEnabled"] = True
            data["EnableLayerIntegrity"] = True
            data["NoLCOWGPU"] = True
            data["RuntimeOptions"][0]["ShareScratch"] = True
            data["SkipSandboxPull"] = True  # we don't need WCOW sandbox, not pulling it makes bootstrap faster
            f.seek(0)
            json.dump(data, f, indent=4)
            f.truncate()

        with tarfile.open(f"{temp_dir}/containerplat.tar", "w:gz") as tar:
            tar.add(temp_dir, arcname="containerplat_build")

        subprocess.run(
            [
                "az",
                "storage",
                "blob",
                "upload",
                "--account-name",
                storage_account,
                "--container-name",
                container_name,
                "--name",
                blob_name,
                "--file",
                f"{temp_dir}/containerplat.tar",
                "--auth-mode",
                "login",
                "--overwrite",
            ],
            check=True,
        )


def vm_create(
    deployment_name: str,
    subscription: str,
    resource_group: str,
    location: str,
    managed_identity: str,
    vm_image: str,
    cplat_feed: str,
    cplat_name: str,
    cplat_version: str,
    cplat_blob_name: str,
    vm_size: str,
    **kwargs,
) -> list[str]:
    """
    :param cplat_feed: ADO feed name for containerplat, can be empty to use existing cache
    :param cplat_name: Name of the containerplat package, can be empty
    :param cplat_version: Version of the containerplat package, can be empty
    :param cplat_blob_name: Name to use for the containerplat blob, can be empty for per-deployment blobs
    """

    if not cplat_blob_name:
        cplat_blob_name = f"containerplat_{deployment_name}"

    if cplat_feed or cplat_name or cplat_version:
        if not cplat_feed or not cplat_name or not cplat_version:
            raise Exception("Missing cplat_feed, cplat_name, or cplat_version (all must be set or all must be empty)")

        containerplat_cache(
            storage_account="cacitestingstorage",
            container_name="container",
            blob_name=cplat_blob_name,
            cplat_feed=cplat_feed,
            cplat_name=cplat_name,
            cplat_version=cplat_version,
        )
    elif not cplat_blob_name:
        raise Exception(
            "An existing cplat_blob_name must be set if cplat_feed, cplat_name, and cplat_version are not set"
        )
    else:
        print(f"Using existing containerplat blob: {cplat_blob_name}")

    print(f"{os.linesep}Deploying VM to Azure, view deployment here:")
    print(
        "%2F".join(
            [
                "https://ms.portal.azure.com/#blade/HubsExtension/DeploymentDetailsBlade/id/",
                "subscriptions",
                subscription,
                "resourceGroups",
                resource_group,
                "providers",
                "Microsoft.Resources",
                "deployments",
                deployment_name,
            ]
        )
    )
    print("")

    password = str(uuid.uuid4())
    password_file = os.path.join(tempfile.gettempdir(), f"{deployment_name}_password.txt")
    with open(password_file, "wt") as f:
        f.write(password)
    print(f"VM password written to {password_file}")

    subprocess.run(
        [
            "az",
            "deployment",
            "group",
            "create",
            "-n",
            deployment_name,
            "--subscription",
            subscription,
            "--resource-group",
            resource_group,
            "--template-file",
            os.path.join(os.path.dirname(__file__), "..", "bicep", "containerplatVM.bicep"),
            "--parameters",
            f"vmPassword={password}",
            "--parameters",
            f"location={location}",  # To be determined by bicep template
            "--parameters",
            "containerPorts=['80']",  # To be determined by bicep template
            "--parameters",
            f"vmImage={vm_image}",
            "--parameters",
            f"managedIDName={managed_identity}",
            "--parameters",
            f"containerplatUrl=https://cacitestingstorage.blob.core.windows.net/container/{cplat_blob_name}",
            "--parameters",
            f"vmSize={vm_size}",
        ],
        check=True,
    )

    ids = vm_get_ids(
        deployment_name=deployment_name,
        subscription=subscription,
        resource_group=resource_group,
    )

    for id in ids:
        if id.endswith("-vm"):
            print(f'Deployed {id.split("/")[-1]}, view here:')
            print(f"https://ms.portal.azure.com/#@microsoft.onmicrosoft.com/resource{id}")

    vm_name = f"{deployment_name}-vm"

    tries = 0
    while tries < 12:
        output = run_on_vm(vm_name, resource_group, "cat C:\\bootstrap.log")
        tries += 1
        if "All done!" in output:
            return ids
        print("Waiting for VM to finish bootstrapping...")
        time.sleep(5)

    raise Exception("VM did not finish bootstrapping in 1m")
