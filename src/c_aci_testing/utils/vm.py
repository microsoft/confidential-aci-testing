#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations

import subprocess
import json
import tempfile
import tarfile
import datetime


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


def generate_storage_sas_key(storage_account: str, container_name: str, path: str):
    res = subprocess.run(
        [
            "az",
            "storage",
            "blob",
            "generate-sas",
            "--as-user",
            "--auth-mode",
            "login",
            "--account-name",
            storage_account,
            "--container-name",
            container_name,
            "--name",
            path,
            "--full-uri",
            "--permissions",
            "acdrw",
            "--expiry",
            (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)).strftime("%Y-%m-%dT%H:%MZ"),
            "--full-uri",
        ],
        check=True,
        stdout=subprocess.PIPE,
    )

    return json.loads(res.stdout.decode("utf-8"))


vm_location_cache = {}


def get_vm_location(resource_group: str, vm_name: str):
    if (resource_group, vm_name) in vm_location_cache:
        return vm_location_cache[(resource_group, vm_name)]

    res = subprocess.run(
        [
            "az",
            "vm",
            "show",
            "-g",
            resource_group,
            "-n",
            vm_name,
            "--query",
            "location",
            "-o",
            "tsv",
        ],
        check=True,
        stdout=subprocess.PIPE,
    )
    location = res.stdout.decode("utf-8").strip()
    vm_location_cache[(resource_group, vm_name)] = location
    return location


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

def download_as_string(url: str):
    res = subprocess.run(
        [
            "curl",
            "-sL",
            url,
        ],
        check=True,
        stdout=subprocess.PIPE,
    )

    return res.stdout.decode("utf-8")


def run_on_vm(
    vm_name: str,
    resource_group: str,
    command: str,
):
    print(f"Running command on VM: {command}")

    STORAGE_ACCOUNT = "cacitestingstorage"
    CONTAINER_NAME = "container"

    run_name = "caciVmRun"  # we can only have one at a time anyway
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S%f")
    stdout_blob_name = f"{vm_name}_{run_name}_{ts}_stdout.txt"
    stderr_blob_name = f"{vm_name}_{run_name}_{ts}_stderr.txt"
    output_blob_url = generate_storage_sas_key(
        storage_account=STORAGE_ACCOUNT,
        container_name=CONTAINER_NAME,
        path=stdout_blob_name,
    )
    error_blob_url = generate_storage_sas_key(
        storage_account=STORAGE_ACCOUNT,
        container_name=CONTAINER_NAME,
        path=stderr_blob_name,
    )

    subprocess.run(
        [
            "az",
            "vm",
            "run-command",
            "create",
            "-g",
            resource_group,
            "--vm-name",
            vm_name,
            "--location",
            get_vm_location(resource_group, vm_name),  # for some reason it needs this
            "--name",
            run_name,
            "--script",
            command,
            "--output-blob-uri",
            output_blob_url,
            "--error-blob-uri",
            error_blob_url,
        ],
        check=True,
        stdout=subprocess.PIPE,
    )

    stdout = download_as_string(output_blob_url)
    stderr = download_as_string(error_blob_url)

    async_delete_storage_blob(STORAGE_ACCOUNT, CONTAINER_NAME, stdout_blob_name)
    async_delete_storage_blob(STORAGE_ACCOUNT, CONTAINER_NAME, stderr_blob_name)

    if stdout:
        print(stdout)
    if stderr:
        print(f"StdErr:\n{stderr}")

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
