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


def upload_configs(storage_account: str, container_name: str, blob_name: str):

    with tempfile.TemporaryDirectory() as temp_dir:
        with open(os.path.join(temp_dir, "lcow-pull-config.json"), "w", encoding="utf-8") as f:
            json.dump({"labels": {"sandbox-platform": "linux/amd64"}}, f)

        with open(os.path.join(temp_dir, "pod.json"), "w", encoding="utf-8") as f:
            json.dump(
                {
                    "metadata": {
                        "name": "sandbox",
                        "namespace": "default",
                        "attempt": 1,
                    },
                    "linux": {"security_context": {"privileged": True}},
                    "annotations": {
                        "io.microsoft.virtualmachine.computetopology.processor.count": "2",
                        "io.microsoft.virtualmachine.computetopology.memory.sizeinmb": "8192",
                        "io.microsoft.virtualmachine.lcow.securitypolicy": "cGFja2FnZSBwb2xpY3kKCmFwaV9zdm4gOj0gIjAuMTAuMCIKCm1vdW50X2RldmljZSA6PSB7ImFsbG93ZWQiOiB0cnVlfQptb3VudF9vdmVybGF5IDo9IHsiYWxsb3dlZCI6IHRydWV9CmNyZWF0ZV9jb250YWluZXIgOj0geyJhbGxvd2VkIjogdHJ1ZSwgImFsbG93X3N0ZGlvX2FjY2VzcyI6IHRydWV9CnVubW91bnRfZGV2aWNlIDo9IHsiYWxsb3dlZCI6IHRydWV9CnVubW91bnRfb3ZlcmxheSA6PSB7ImFsbG93ZWQiOiB0cnVlfQpleGVjX2luX2NvbnRhaW5lciA6PSB7ImFsbG93ZWQiOiB0cnVlfQpleGVjX2V4dGVybmFsIDo9IHsiYWxsb3dlZCI6IHRydWUsICJhbGxvd19zdGRpb19hY2Nlc3MiOiB0cnVlfQpzaHV0ZG93bl9jb250YWluZXIgOj0geyJhbGxvd2VkIjogdHJ1ZX0Kc2lnbmFsX2NvbnRhaW5lcl9wcm9jZXNzIDo9IHsiYWxsb3dlZCI6IHRydWV9CnBsYW45X21vdW50IDo9IHsiYWxsb3dlZCI6IHRydWV9CnBsYW45X3VubW91bnQgOj0geyJhbGxvd2VkIjogdHJ1ZX0KZ2V0X3Byb3BlcnRpZXMgOj0geyJhbGxvd2VkIjogdHJ1ZX0KZHVtcF9zdGFja3MgOj0geyJhbGxvd2VkIjogdHJ1ZX0KcnVudGltZV9sb2dnaW5nIDo9IHsiYWxsb3dlZCI6IHRydWV9CmxvYWRfZnJhZ21lbnQgOj0geyJhbGxvd2VkIjogdHJ1ZX0Kc2NyYXRjaF9tb3VudCA6PSB7ImFsbG93ZWQiOiB0cnVlfQpzY3JhdGNoX3VubW91bnQgOj0geyJhbGxvd2VkIjogdHJ1ZX0K",
                    },
                },
                f,
            )

        with open(os.path.join(temp_dir, "lcow-container.json"), "w", encoding="utf-8") as f:
            json.dump(
                {
                    "metadata": {"name": "examples"},
                    "image": {"image": "hello-world:latest"},
                    "linux": {"security_context": {"privileged": True}},
                    "forwardPorts": [],
                },
                f,
            )

        with tarfile.open(f"{temp_dir}/lcow_config.tar", "w:gz") as tar:
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


def run_on_vm(
    vm_name: str,
    resource_group: str,
    command: str,
):
    subprocess.run(
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
    )


def vm_deploy(
    target_path: str,
    deployment_name: str,
    subscription: str,
    resource_group: str,
    location: str,
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
        storage_account="cacitestingstorage",
        container_name="container",
        blob_name="lcow_config",
    )

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
        ],
        check=True,
    )

    def run_on_vm_cmd(command):
        run_on_vm(
            resource_group=resource_group,
            vm_name=f"{deployment_name}-vm",
            command=command,
        )

    run_on_vm_cmd("dir /containerplat")

    return []
