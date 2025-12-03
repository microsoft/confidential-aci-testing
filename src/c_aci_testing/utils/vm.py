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
    storage_account: str,
    container_name: str,
    file_path: str,
    out_file: str,
    binary: bool,
):
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S%f")
    blob_name = f"{vm_name}_{ts}_download"
    blobUrl = f"https://{storage_account}.blob.core.windows.net/{container_name}/{blob_name}"

    maybeBinary = "-Binary" if binary else ""

    run_on_vm(
        vm_name=vm_name,
        subscription=subscription,
        resource_group=resource_group,
        command=f'C:\\storage_put.ps1 -Uri "{blobUrl}" -InFile "{file_path}" {maybeBinary}',
    )

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
            out_file,
        ],
        check=True,
        stdout=subprocess.PIPE,
    )
    async_delete_storage_blob(storage_account, container_name, blob_name)


def upload_to_vm_and_run(
    src: str,
    dst: str,
    subscription: str,
    resource_group: str,
    vm_name: str,
    storage_account: str,
    container_name: str,
    blob_name: str,
    commands: List[str],
) -> str:
    """
    :return: stdout
    """

    dst_parsed = re.fullmatch(r"^(.+):\\(.*)$", dst)
    if not dst_parsed:
        raise ValueError("Destination path must be absolute")
    dst_drive, dst_arcname = dst_parsed.groups()
    if not dst_drive.isalpha():
        raise ValueError(f"Invalid destination path {dst}")
    dst_arcname = dst_arcname.rstrip("\\").replace("\\", "/")

    with tempfile.TemporaryDirectory() as temp_dir:
        with tarfile.open(f"{temp_dir}/upload.tar", "w:gz") as tar:
            if dst_arcname:
                tar.add(src, arcname=dst_arcname)  # tarfile will handle directory for us
            else:
                # we're extracting to a drive root. Add each item in src individually
                for item in os.listdir(src):
                    tar.add(os.path.join(src, item), arcname=item)

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

    blobUrl = f"https://{storage_account}.blob.core.windows.net/{container_name}/{blob_name}"

    output = run_on_vm(
        vm_name=vm_name,
        subscription=subscription,
        resource_group=resource_group,
        command="\r\n".join(
            [
                f"if (Test-Path C:/upload.tar) {{ rm -Force C:/upload.tar }}",
                *(
                    [
                        f"if (Test-Path '{dst}') {{ rm -Recurse -Force '{dst}' }}",
                    ]
                    if dst_arcname
                    else []
                ),
                f'C:\\storage_get.ps1 -Uri "{blobUrl}" -OutFile C:\\upload.tar',
                f"tar -xf C:\\upload.tar -C {dst_drive}:/",
                f"if ($LASTEXITCODE -ne 0) {{",
                f"  throw 'Failed to extract tar file'",
                f"}}",
                *commands,
            ]
        ),
    )

    async_delete_storage_blob(storage_account, container_name, blob_name)

    return output


def decode_utf8_or_utf16(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("utf-16")
