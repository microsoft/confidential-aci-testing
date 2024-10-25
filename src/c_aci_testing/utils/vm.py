#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations
from typing import List

import subprocess
import json
import tempfile
import tarfile
import datetime
import os
import re


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


def async_delete_storage_blob(storage_account: str, container_name: str, blob_name: str):
    subprocess.Popen(
        [
            "az",
            "storage",
            "blob",
            "delete",
            "--account-name",
            storage_account,
            "--container-name",
            container_name,
            "--name",
            blob_name,
            "--auth-mode",
            "login",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def download_storage_blob(storage_account: str, container_name: str, blob_name: str) -> bytes:
    temp_file = tempfile.mktemp()
    subprocess.run(
        [
            "az",
            "storage",
            "blob",
            "download",
            "--account-name",
            storage_account,
            "--container-name",
            container_name,
            "--name",
            blob_name,
            "--auth-mode",
            "login",
            "--file",
            temp_file,
        ],
        check=True,
        stdout=subprocess.PIPE,
    )

    with open(temp_file, "rb") as f:
        data = f.read()

    os.remove(temp_file)

    return data


### NOTE on output truncation ###
# az vm run-command invoke does not give you the full output.
# There is a way to stream output to a storage account via az vm run-command create --output-blob-uri,
# but it is very unreliable - sometimes the output file just doesn't show up in the storage account at
# all.
# Therefore I've simply gave up on trying to obtain the full output. You might be able to wrap the
# command in powershell and redirect output to a file, then upload that file to the storage account.


def run_on_vm(
    vm_name: str,
    subscription: str,
    resource_group: str,
    command: str,
) -> str:
    """
    :return: stdout
    """

    print(f"Running command on VM: {command}")
    res = subprocess.run(
        [
            "az",
            "vm",
            "run-command",
            "invoke",
            "--subscription",
            subscription,
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

    if stdout:
        print(stdout)
    if stderr:
        print(f"StdErr:\n{stderr}")

    if stdout is None:
        raise Exception("No StdOut in response")

    return stdout


def download_single_file_from_vm(
    vm_name: str,
    subscription: str,
    resource_group: str,
    managed_identity: str,
    storage_account: str,
    container_name: str,
    file_path: str,
) -> bytes:
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S%f")
    blob_name = f"{vm_name}_{ts}_download"
    blobUrl = f"https://{storage_account}.blob.core.windows.net/{container_name}/{blob_name}"
    tokenUrl = tokenImdsUrl(
        getManagedIdentityClientId(subscription, resource_group, managed_identity), "https://storage.azure.com/"
    )
    date_str = datetime.datetime.now(datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    # -InFile requires file to not be open by ">>", but for some reason `Get-Content` works

    run_on_vm(
        vm_name=vm_name,
        subscription=subscription,
        resource_group=resource_group,
        command=" ; ".join(
            [
                '$ProgressPreference = "SilentlyContinue"',  # otherwise invoke-restmethod is very slow to download large files
                f'$token = (Invoke-RestMethod -Uri "{tokenUrl}" -Headers @{{Metadata="true"}} -Method GET -UseBasicParsing).access_token',
                f'$headers = @{{ Authorization = "Bearer $token"; "x-ms-version" = "2019-12-12"; "x-ms-blob-type"="BlockBlob"; "x-ms-date"="{date_str}" }}',
                f'Invoke-RestMethod -Uri "{blobUrl}" -Method PUT -Headers $headers -Body (Get-Content -Raw "{file_path}")',
            ]
        ),
    )

    data = download_storage_blob(storage_account, container_name, blob_name)
    async_delete_storage_blob(storage_account, container_name, blob_name)
    return data


def upload_to_vm_and_run(
    src: str,
    dst: str,
    subscription: str,
    resource_group: str,
    vm_name: str,
    storage_account: str,
    container_name: str,
    blob_name: str,
    managed_identity: str,
    commands: List[str],
) -> str:
    """
    :return: stdout
    """

    dst_parsed = re.fullmatch(r"^(.+):\\(.+)$", dst)
    if not dst_parsed:
        raise ValueError("Destination path must be absolute")
    dst_drive, dst_arcname = dst_parsed.groups()
    if not dst_drive.isalpha():
        raise ValueError(f"Invalid destination path {dst}")
    dst_arcname = dst_arcname.rstrip("\\")
    if not dst_arcname:
        raise ValueError(f"Copying directly to {dst_drive}:\\ is not supported")
    dst_arcname = dst_arcname.replace("\\", "/")

    with tempfile.TemporaryDirectory() as temp_dir:
        with tarfile.open(f"{temp_dir}/upload.tar", "w:gz") as tar:
            tar.add(src, arcname=dst_arcname)

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

    return run_on_vm(
        vm_name=vm_name,
        subscription=subscription,
        resource_group=resource_group,
        command="try { "
        + "\r\n".join(
            [
                f'$ProgressPreference = "SilentlyContinue"',  # otherwise invoke-restmethod is very slow to download large files
                f'$ErrorActionPreference = "Continue"',
                f'$token = (Invoke-RestMethod -Uri "{tokenUrl}" -Headers @{{Metadata="true"}} -Method GET -UseBasicParsing).access_token',
                f'Write-Output "Token acquired"',
                f"if (Test-Path C:/upload.tar) {{ rm -Force C:/upload.tar }}",
                f"if (Test-Path '{dst}') {{ rm -Recurse -Force '{dst}' }}",
                f'$headers = @{{ Authorization = "Bearer $token"; "x-ms-version" = "2019-12-12" }}',
                f"Invoke-RestMethod -Uri '{blobUrl}' -Method GET -Headers $headers -OutFile 'C:/upload.tar'",
                f'Write-Output "download done"',
                f"tar -xf C:/upload.tar -C {dst_drive}:/",
                f'Write-Output "tar result: $LASTEXITCODE"',
                f"if ($LASTEXITCODE -ne 0) {{",
                f"  throw 'Failed to extract tar file'",
                f"}}",
                *commands,
            ]
        )
        + " } catch {\r\n  Write-Output $_.Exception.ToString()\r\nthrow\r\n}",
    )


def decode_utf8_or_utf16(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("utf-16")
