#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import base64
import json
import os
import subprocess
import tarfile
import tempfile

from c_aci_testing.tools.vm_get_ids import vm_get_ids
from c_aci_testing.utils.parse_bicep import parse_bicep
from c_aci_testing.utils.run_on_vm import run_on_vm


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


def get_aci_token():
    res = subprocess.run(
        ["az", "acr", "login", "-n", "cacitesting", "--expose-token"],
        stdout=subprocess.PIPE,
        check=True,
    )
    return json.loads(res.stdout)["accessToken"]


def make_configs(
    target_path: str,
    subscription: str,
    resource_group: str,
    deployment_name: str,
    registry: str,
    repository: str,
    tag: str,
    output_conf_dir: str,
):

    lcow_config_dir = os.path.join(os.path.dirname(__file__), "..", "templates", "lcow_configs")

    # run_script = [r"Set-Alias -Name crictl -Value C:\ContainerPlat\crictl.exe"]
    # pull_commands = []
    # start_commands = []

    # aci_pull_token = get_aci_token()

    with open(
        os.path.join(lcow_config_dir, "pull.json.template"),
        encoding="utf-8",
    ) as pull_template_file:
        pull_template = json.load(pull_template_file)

    with open(
        os.path.join(lcow_config_dir, "container.json.template"),
        encoding="utf-8",
    ) as container_template_file:
        container_template = json.load(container_template_file)

    with open(
        os.path.join(lcow_config_dir, "container_group.json.template"),
        encoding="utf-8",
    ) as container_group_template_file:
        container_group_template = json.load(container_group_template_file)

    with open(
        os.path.join(output_conf_dir, "pull.json"),
        encoding="utf-8",
        mode="w",
    ) as pull_file:
        json.dump(pull_template, pull_file, separators=(",", ":"))

    for container_group_id, container_group, containers in parse_bicep(
        target_path,
        subscription,
        resource_group,
        deployment_name,
        registry,
        repository,
        tag,
    ):
        group_cpus = 0
        group_memory = 0
        for container in containers:
            # pull_commands.append(
            #     " ".join(
            #         [
            #             "crictl pull",
            #             f'--creds "00000000-0000-0000-0000-000000000000:{aci_pull_token}"',
            #             "--pod-config ./pull.json",
            #             container["properties"]["image"],
            #         ]
            #     )
            # )

            container_id = container["name"]
            group_cpus += container["properties"]["resources"]["requests"]["cpu"]
            group_memory += container["properties"]["resources"]["requests"]["memoryInGB"]
            with open(
                os.path.join(output_conf_dir, f"container_{container_group_id}_{container_id}.json"),
                "w",
                encoding="utf-8",
            ) as f:
                container_json = container_template.copy()
                container_json["metadata"]["name"] = container_id
                container_json["image"]["image"] = container["properties"]["image"]
                container_json["forwardPorts"] = [port["port"] for port in container["properties"]["ports"]]
                json.dump(container_json, f, separators=(",", ":"))

        with open(
            os.path.join(output_conf_dir, f"container_group_{container_group_id}.json"),
            "w",
            encoding="utf-8",
        ) as f:
            container_group_json = container_group_template.copy()
            annotations = container_group_json["annotations"]
            annotations["io.microsoft.virtualmachine.computetopology.processor.count"] = str(group_cpus)
            annotations["io.microsoft.virtualmachine.computetopology.memory.sizeinmb"] = str(group_memory * 1024)

            print("Until generated policies are supported, using the allow all policy")
            # security_policy = container_group["properties"]["confidentialComputeProperties"]["ccePolicy"]
            # if "parameters('ccePolicies')" in security_policy:
            #     raise Exception("ccePolicies parameter not resolved, run c-aci-testing policies gen first")
            with open(
                os.path.join(os.path.dirname(__file__), "..", "templates", "allow_all_policy.rego"), "r"
            ) as policy_file:
                security_policy = base64.b64encode(policy_file.read().encode("utf-8")).decode("utf-8")

            annotations["io.microsoft.virtualmachine.lcow.securitypolicy"] = security_policy

            json.dump(container_group_json, f, separators=(",", ":"))


def construct_command(
    target_path: str,
    subscription: str,
    resource_group: str,
    deployment_name: str,
    registry: str,
    repository: str,
    tag: str,
):

    res = subprocess.run(
        ["az", "acr", "login", "-n", "cacitesting", "--expose-token"],
        stdout=subprocess.PIPE,
        check=True,
    )
    token = json.loads(res.stdout)["accessToken"]

    command = []

    args = {
        "target_path": target_path,
        "subscription": subscription,
        "resource_group": resource_group,
        "deployment_name": deployment_name,
        "registry": registry,
        "repository": repository,
        "tag": tag,
    }

    for _, _, containers in parse_bicep(**args):
        for container in containers:
            # Pull images
            command.append(
                " ".join(
                    [
                        "/containerplat/crictl.exe pull",
                        f'--creds "00000000-0000-0000-0000-000000000000:{token}"',
                        "--pod-config ./pull.json",
                        container["properties"]["image"],
                    ]
                )
            )

    for container_group_id, _, containers in parse_bicep(**args):
        # Start Container Group
        command.append(
            " ".join(
                [
                    "$group_id = (/containerplat/crictl.exe runp",
                    "--runtime runhcs-lcow",
                    f"./container_group_{container_group_id}.json)",
                ]
            )
        )

        for container in containers:

            # Create Container
            command.append(
                " ".join(
                    [
                        "$container_id = (/containerplat/crictl.exe create",
                        "--no-pull",
                        "$group_id",
                        f'./container_{container_group_id}_{container["name"]}.json',
                        f"./container_group_{container_group_id}.json)",
                    ]
                )
            )

            # Start Container
            command.append(
                " ".join(
                    [
                        "/containerplat/crictl.exe start",
                        "$container_id",
                    ]
                )
            )

    return command


def vm_runc(
    target_path: str,
    deployment_name: str,
    subscription: str,
    resource_group: str,
    managed_identity: str,
    registry: str,
    repository: str,
    tag: str,
    **kwargs,
):
    lcow_config_blob_name = f"lcow_config_{deployment_name}"
    storage_account = "cacitestingstorage"
    vm_name = f"{deployment_name}-vm"

    with tempfile.TemporaryDirectory() as temp_dir:
        print("Constructing LCOW configs")

        make_configs(
            target_path=target_path,
            subscription=subscription,
            resource_group=resource_group,
            deployment_name=deployment_name,
            registry=registry,
            repository=repository,
            tag=tag,
            output_conf_dir=temp_dir,
        )

        print("Constructing run.ps1")

        commands = construct_command(
            target_path=target_path,
            subscription=subscription,
            resource_group=resource_group,
            deployment_name=deployment_name,
            registry=registry,
            repository=repository,
            tag=tag,
        )

        with open(f"{temp_dir}/run.ps1", "wb") as f:
            f.write("\r\n".join(commands).encode("utf-8"))

        print(f"Uploading LCOW config in {temp_dir} to {vm_name}...")

        upload_to_vm_and_run(
            target_path=temp_dir,
            vm_path="C:\\lcow",
            subscription=subscription,
            resource_group=resource_group,
            vm_name=vm_name,
            storage_account=storage_account,
            container_name="container",
            blob_name=lcow_config_blob_name,
            managed_identity=managed_identity,
            run_script="run.ps1",
        )

    run_on_vm(
        resource_group=resource_group,
        vm_name=f"{deployment_name}-vm",
        command="/containerplat/crictl.exe ps",
    )
