#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations

import subprocess
import json
import tempfile
import tarfile


def tokenImdsUrl(client_id: str, resource: str):
    return f"http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource={resource}&client_id={client_id}"


def getManagedIdentityClientId(subscription: str, resource_group: str, managed_identity: str):
    res = subprocess.run(
        [
            "az",
            "resource",
            "show",
            "--subscription",
            subscription,
            "--resource-group",
            resource_group,
            "--name",
            managed_identity,
            "--resource-type",
            "Microsoft.ManagedIdentity/userAssignedIdentities",
        ],
        check=True,
        stdout=subprocess.PIPE,
    )
    return json.loads(res.stdout)["properties"]["clientId"]


def run_on_vm(
    vm_name: str,
    resource_group: str,
    command: str,
):
    print(f"Running command on VM: {command}")
    res = subprocess.run(
        [
            "az",
            "vm",
            "run-command",
            "invoke",
            "-g",
            resource_group,
            "-n",
            vm_name,
            "--command-id",
            "RunPowerShellScript",
            "--scripts",
            command,
        ],
        check=True,
        stdout=subprocess.PIPE,
    )
    out = json.loads(res.stdout)

    stderr = ""
    for value in out["value"]:
        if "StdErr" in value["code"]:
            stderr = value["message"]

    stdout = None
    for value in out["value"]:
        if "StdOut" in value["code"]:
            stdout = value["message"]

    if stderr:
        print(f"StdErr:\n{stderr}")
    if stdout:
        print(stdout)

    if stdout is None:
        raise Exception("No StdOut in response")

    return stdout


def upload_to_vm_and_run(
    target_path: str,
    vm_path: str,
    subscription: str,
    resource_group: str,
    vm_name: str,
    storage_account: str,
    container_name: str,
    blob_name: str,
    managed_identity: str,
    run_script: str,
):
    """
    Download a directory onto the VM through the storage account and optionally run a script.

    :param run_script: The name of a script within target_path to run on the VM, or empty.
    """

    if vm_path.endswith("/") or vm_path.endswith("\\"):
        vm_path = vm_path[:-1]

    with tempfile.TemporaryDirectory() as temp_dir:
        with tarfile.open(f"{temp_dir}/upload.tar", "w:gz") as tar:
            tar.add(target_path, arcname="upload")

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
                f"{temp_dir}/upload.tar",
                "--auth-mode",
                "login",
                "--overwrite",
            ],
            check=True,
        )

    tokenUrl = tokenImdsUrl(
        getManagedIdentityClientId(subscription, resource_group, managed_identity), "https://storage.azure.com/"
    )
    blobUrl = f"https://{storage_account}.blob.core.windows.net/{container_name}/{blob_name}"
    scriptCmd = []
    if run_script:
        scriptCmd = [f"cd {vm_path}", vm_path + "\\" + run_script, 'Write-Output "Script result: $LASTEXITCODE"']

    run_on_vm(
        vm_name,
        resource_group,
        "try { "
        + " ; ".join(
            [
                '$ProgressPreference = "SilentlyContinue"',  # otherwise invoke-restmethod is very slow to download large files
                '$ErrorActionPreference = "Continue"',
                f'$token = (Invoke-RestMethod -Uri "{tokenUrl}" -Headers @{{Metadata="true"}} -Method GET -UseBasicParsing).access_token',
                'Write-Output "Token acquired"',
                "if (Test-Path C:/upload.tar) { rm -Force C:/upload.tar }",
                "if (Test-Path C:/upload) {{ rm -Recurse -Force C:/upload }}",
                f"if (Test-Path {vm_path}) {{ rm -Recurse -Force {vm_path} }}",
                '$headers = @{ Authorization = "Bearer $token"; "x-ms-version" = "2019-12-12" }',
                f'Invoke-RestMethod -Uri "{blobUrl}" -Method GET -Headers $headers -OutFile "C:/upload.tar"',
                'Write-Output "download done"',
                "tar -xf C:/upload.tar -C C:/",
                f"mv C:/upload {vm_path}",
                'Write-Output "result: $LASTEXITCODE"',
                *scriptCmd,
            ]
        )
        + " } catch { Write-Output $_.Exception.ToString() }",
    )
