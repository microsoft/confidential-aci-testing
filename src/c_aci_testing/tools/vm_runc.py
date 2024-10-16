#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile

from c_aci_testing.utils.parse_bicep import parse_bicep
from c_aci_testing.utils.vm import run_on_vm
from ..utils.vm import upload_to_vm_and_run


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

    run_script = [r"Set-Alias -Name crictl -Value C:\ContainerPlat\crictl.exe"]
    pull_commands = run_script.copy()
    start_pod_commands = run_script.copy()
    start_container_commands = run_script.copy()
    check_commands = run_script.copy()

    aci_pull_token = get_aci_token()

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

        start_pod_commands.append(
            " ".join(
                [
                    "$group_id = (/containerplat/crictl.exe runp",
                    "--runtime runhcs-lcow",
                    f"./container_group_{container_group_id}.json)",
                ]
            )
        )

        for container in containers:
            pull_commands.append(
                " ".join(
                    [
                        "crictl pull",
                        f'--creds "00000000-0000-0000-0000-000000000000:{aci_pull_token}"',
                        "--pod-config ./pull.json",
                        container["properties"]["image"],
                    ]
                )
            )

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

            # Create Container
            start_container_commands.append(
                " ".join(
                    [
                        "$container_id = (crictl create --no-pull",
                        "(crictl pods --name sandbox -q)",  # TODO: support different pod names
                        f'./container_{container_group_id}_{container["name"]}.json',
                        f"./container_group_{container_group_id}.json)",
                    ]
                )
            )

            # Start Container
            start_container_commands.append("crictl start $container_id")

            check_commands.append(f"$res=(crictl exec (crictl ps --name {container_id} -q) echo Hello)")
            check_commands.append(f"if ($res -ne 'Hello') {{ Write-Host 'ERROR: exec failed on {container_id}' }}")

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

    def write_script(file, script):
        with open(os.path.join(output_conf_dir, file), "w", encoding="utf-8") as f:
            f.write("\r\n".join(script))

    write_script("pull.ps1", pull_commands)
    write_script("runp.ps1", start_pod_commands)
    write_script("startc.ps1", start_container_commands)
    write_script("check.ps1", check_commands)

    write_script(
        "run.ps1",
        [
            ".\\pull.ps1",
            ".\\runp.ps1",
            ".\\startc.ps1",
            ".\\check.ps1",
        ],
    )


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

        print(f"Uploading LCOW config and scripts in {temp_dir} to {vm_name}...")

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
