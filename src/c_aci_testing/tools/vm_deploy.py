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
import uuid

from c_aci_testing.utils.parse_bicep import parse_bicep


def containerplat_cache(storage_account: str, container_name: str, blob_name: str):
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
                "ContainerPlat-Prod",
                "--name",
                "containerplat-confidential-aci",
                "--version",
                "0.1.3",
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


def upload_configs(
    target_path: str,
    subscription: str,
    resource_group: str,
    deployment_name: str,
    registry: str,
    repository: str,
    tag: str,
    storage_account: str,
    container_name: str,
    blob_name: str,
):

    with tempfile.TemporaryDirectory() as temp_dir:

        lcow_config_dir = os.path.join(os.path.dirname(__file__), "..", "templates", "lcow_configs")

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
            os.path.join(temp_dir, "pull.json"),
            encoding="utf-8",
            mode="w",
        ) as pull_file:
            json.dump(pull_template, pull_file, separators=(",", ":"))

        for container_group_id, container_group, containers in parse_bicep(
            target_path, subscription, resource_group, deployment_name, registry, repository, tag,
        ):
            group_cpus = 0
            group_memory = 0
            for container in containers:
                container_id = container["name"]
                group_cpus += container["properties"]["resources"]["requests"]["cpu"]
                group_memory += container["properties"]["resources"]["requests"]["memoryInGB"]
                with open(
                    os.path.join(temp_dir, f"container_{container_group_id}_{container_id}.json"),
                    "w",
                    encoding="utf-8",
                ) as f:
                    container_json = container_template.copy()
                    container_json["metadata"]["name"] = container_id
                    container_json["image"]["image"] = container["properties"]["image"]
                    container_json["forwardPorts"] = [port["port"] for port in container["properties"]["ports"]]
                    json.dump(container_json, f, separators=(",", ":"))

            with open(
                os.path.join(temp_dir, f"container_group_{container_group_id}.json"),
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
                with open(os.path.join(os.path.dirname(__file__), "..", "templates", "allow_all_policy.rego"), "r") as policy_file:
                    security_policy = base64.b64encode(policy_file.read().encode("utf-8")).decode("utf-8")

                annotations["io.microsoft.virtualmachine.lcow.securitypolicy"] = security_policy

                json.dump(container_group_json, f, separators=(",", ":"))

        with tarfile.open(f"{temp_dir}/lcow_config.tar", "w:gz") as tar:
            for file in os.listdir(temp_dir):
                print(file)
                print(open(os.path.join(temp_dir, file), "r").read())
            tar.add(temp_dir, arcname="lcow_config")

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
                f"{temp_dir}/lcow_config.tar",
                "--auth-mode",
                "login",
                "--overwrite",
            ],
            check=True,
        )


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
                        "--pod-config /lcow_config/pull.json",
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
                    f"/lcow_config/container_group_{container_group_id}.json)",
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
                        f'/lcow_config/container_{container_group_id}_{container["name"]}.json',
                        f"/lcow_config/container_group_{container_group_id}.json)",
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
    print(res.stdout.decode("utf-8"))
    for value in json.loads(res.stdout)["value"]:
        if "StdOut" in value["code"]:
            return value["message"]
    raise Exception("No StdOut in response")


def vm_deploy(
    target_path: str,
    deployment_name: str,
    subscription: str,
    resource_group: str,
    location: str,
    registry: str,
    repository: str,
    tag: str,
    managed_identity: str,
    vm_image: str,
    **kwargs,
) -> list[str]:

    containerplat_cache(
        storage_account="cacitestingstorage",
        container_name="container",
        blob_name="containerplat",
    )

    upload_configs(
        target_path=target_path,
        subscription=subscription,
        resource_group=resource_group,
        deployment_name=deployment_name,
        registry=registry,
        repository=repository,
        tag=tag,
        storage_account="cacitestingstorage",
        container_name="container",
        blob_name="lcow_config",
    )

    print(f"{os.linesep}Deploying to Azure, view deployment here:")
    print("%2F".join([
        "https://ms.portal.azure.com/#blade/HubsExtension/DeploymentDetailsBlade/id/",
        "subscriptions", subscription,
        "resourceGroups", resource_group,
        "providers", "Microsoft.Resources", "deployments", deployment_name,
    ]))
    print("")

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
            f"vmPassword={uuid.uuid4()}",
            "--parameters",
            f"location={location}",  # To be determined by bicep template
            "--parameters",
            "containerPorts=['80']",  # To be determined by bicep template
            "--parameters",
            f"vmImage={vm_image}",
            "--parameters",
            f"managedIDName={managed_identity}",
            "--parameters",
            "containerplatUrl=https://cacitestingstorage.blob.core.windows.net/container/containerplat",
            "--parameters",
            "lcowConfigUrl=https://cacitestingstorage.blob.core.windows.net/container/lcow_config",
            "--parameters",
            f"vmCustomCommands={construct_command(
                target_path,
                subscription,
                resource_group,
                deployment_name,
                registry,
                repository,
                tag,
            )}",
        ],
        check=True,
    )

    run_on_vm(
        resource_group=resource_group,
        vm_name=f"{deployment_name}-vm",
        command="/containerplat/crictl.exe ps",
    )

    return []
