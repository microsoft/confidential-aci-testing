#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time

from c_aci_testing.utils.parse_bicep import parse_bicep
from c_aci_testing.utils.vm import run_on_vm
from ..utils.vm import upload_to_vm_and_run
from c_aci_testing.tools.vm_create import VM_CONTAINER_NAME


# TODO: ideally all of this should happen within the VM, and there can be powershell logic to use the correct ACR instance even if "registry" is wrong etc.
def get_acr_token(registry: str):
    if registry.endswith(".azurecr.io"):
        registry = registry[: -len(".azurecr.io")]

    tries = 0
    while tries < 5:
        try:
            res = subprocess.run(
                ["az", "acr", "login", "-n", registry, "--expose-token"],
                stdout=subprocess.PIPE,
                stderr=None,  # inherit
                check=True,
            )
            return json.loads(res.stdout)["accessToken"]
        except subprocess.CalledProcessError:
            tries += 1
            time.sleep(1)
    raise Exception("Failed to get ACR token in 5 tries")


def make_configs(
    target_path: str,
    subscription: str,
    resource_group: str,
    deployment_name: str,
    win_flavor: str,
    registry: str,
    repository: str,
    tag: str,
    prefix: str,
    output_conf_dir: str,
):

    lcow_config_dir = os.path.join(os.path.dirname(__file__), "..", "templates", "lcow_configs")

    run_script_common = [
        r"Set-Alias -Name crictl -Value C:\ContainerPlat\crictl.exe",
        f"cd C:\\{prefix}",
    ]

    checked_shimdiag_exec_pod_fn = "\r\n".join(
        [
            "Set-Alias -Name shimdiag -Value C:\\ContainerPlat\\shimdiag.exe",
            "function shimdiag_exec_pod {",
            "  param(",
            "    [string]$podName,",
            "    [switch]$t,",
            "    [parameter(ValueFromRemainingArguments=$true)]",
            "    [string[]]$argv",  # can't use $args
            "  )",
            "  $podId=(crictl pods --name $podName -q)",
            '  if (!$podId) { throw "Pod $podName not found"; }',
            "  $opts = @()",
            "  if ($t) { $opts += '-t' }",
            '  shimdiag exec @opts ("k8s.io-"+$podId) $argv',
            "}",
        ]
    )
    checked_container_exec_fn = "\r\n".join(
        [
            "function container_exec {",
            "  param(",
            "    [string]$podName,",
            "    [string]$containerName,",
            "    [switch]$it,",
            "    [parameter(ValueFromRemainingArguments=$true)]",
            "    [string[]]$argv",  # can't use $args
            "  )",
            "  $podId=(crictl pods --name $podName -q)",
            '  if (!$podId) { throw "Pod $podName not found"; }',
            "  $containerId=(crictl ps --pod $podId --name $containerName -q)",
            '  if (!$containerId) { throw "Container $containerName not found in pod $podName"; }',
            "  $opts = @()",
            "  if ($it) { $opts += '-it' }",
            "  crictl exec @opts $containerId $argv",
            "}",
        ]
    )
    pull_commands = run_script_common.copy()
    start_pod_commands = run_script_common.copy()
    start_container_commands = run_script_common.copy()
    check_commands = [
        *run_script_common,
        checked_shimdiag_exec_pod_fn,
        checked_container_exec_fn,
    ]
    stop_container_commands = run_script_common.copy()
    stop_pod_commands = run_script_common.copy()

    if registry.endswith(".azurecr.io"):
        aci_pull_token = get_acr_token(registry)
    else:
        aci_pull_token = ""

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

    if win_flavor == "ws2022":
        del container_group_template["annotations"]["io.microsoft.virtualmachine.lcow.hcl-enabled"]

    with open(
        os.path.join(output_conf_dir, "pull.json"),
        encoding="utf-8",
        mode="w",
    ) as pull_file:
        json.dump(pull_template, pull_file, indent=2)

    def write_script(file, script):
        with open(os.path.join(output_conf_dir, file), "w", encoding="utf-8") as f:
            f.write("\r\n".join(script))

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

        pod_name = f"{prefix}_{container_group_id}"

        start_pod_commands.append(
            " ".join(
                [
                    "$group_id = (crictl runp",
                    "--runtime runhcs-lcow",
                    f"./container_group_{container_group_id}.json)",
                ]
            )
        )

        shimdiag_exec_pod = f'shimdiag_exec_pod -podName "{pod_name}" --'

        write_script(
            f"stream_dmesg_{container_group_id}.ps1",
            [
                *run_script_common,
                checked_shimdiag_exec_pod_fn,
                f"echo '-------- pod {pod_name} started --------' >> dmesg_{container_group_id}.log",
                f"{shimdiag_exec_pod} dmesg -w >> dmesg_{container_group_id}.log",
            ],
        )

        start_pod_commands.append(
            f"Start-Process powershell -WorkingDirectory . -ArgumentList /c,.\\stream_dmesg_{container_group_id}.ps1"
        )

        stop_pod_commands.append(
            "; ".join(
                [
                    f"$podId = crictl pods --name {pod_name} -q",
                    "if ($podId) { crictl stopp $podId",
                    "crictl rmp $podId }",
                ]
            )
        )

        write_script(
            f"connect_{container_group_id}.ps1",
            [
                "param(",
                "  [parameter(ValueFromRemainingArguments=$true)][string[]]$argv",
                ")",
                *run_script_common,
                checked_shimdiag_exec_pod_fn,
                "if (!$argv) {",
                "  $argv = @('bash')",
                "}",
                f"shimdiag_exec_pod -podName '{pod_name}' -t -- @argv",
            ],
        )

        # With just a simple echo, very occasionally, the exec won't return any output, but the pod is still fine.
        check_commands.append(f"$res=({shimdiag_exec_pod} sh -c 'echo PodAlive!!; sleep 1')")
        check_commands.extend(
            [
                "if ($res -ne 'PodAlive!!') {",
                f"  Write-Output 'ERROR: exec failed on pod {pod_name}'",
                "  $hasError = $true",
                "}",
            ]
        )

        # check_commands.append(
        #     "\r\n".join(
        #         [
        #             f'$dmesg={shimdiag_exec_pod} dmesg',
        #             "if (-not $dmesg) {",
        #             f"  Write-Output 'ERROR: dmesg failed on pod {pod_name}'",
        #             "  $hasError = $true",
        #             "}",
        #             "Write-Output $dmesg",
        #         ]
        #     )
        # )

        for container in containers:
            pull_commands.append(
                " ".join(
                    [
                        "crictl pull",
                        (f'--creds "00000000-0000-0000-0000-000000000000:{aci_pull_token}"' if aci_pull_token else ""),
                        "--pod-config ./pull.json",
                        container["properties"]["image"],
                    ]
                )
            )

            container_id = container["name"]
            container_name = f"{prefix}_{container_group_id}_{container_id}"
            group_cpus += container["properties"]["resources"]["requests"]["cpu"]
            group_memory += container["properties"]["resources"]["requests"]["memoryInGB"]
            with open(
                os.path.join(output_conf_dir, f"container_{container_group_id}_{container_id}.json"),
                "w",
                encoding="utf-8",
            ) as f:
                container_json = container_template.copy()
                container_json["metadata"]["name"] = container_name
                container_json["image"]["image"] = container["properties"]["image"]
                if "ports" in container["properties"]:
                    container_json["forwardPorts"] = [port["port"] for port in container["properties"]["ports"]]
                if "command" in container["properties"]:
                    container_json["command"] = container["properties"]["command"]
                if "environmentVariables" in container["properties"]:
                    container_json["envs"] = [
                        {"key": env["name"], "value": env["value"]}
                        for env in container["properties"]["environmentVariables"]
                    ]
                container_json["log_path"] = f"C:\\{prefix}\\container_log_{container_group_id}_{container_id}.log"
                json.dump(container_json, f, indent=2)

            # Create Container
            start_container_commands.append(
                " ".join(
                    [
                        "$container_id = (crictl create --no-pull",
                        f"(crictl pods --name {pod_name} -q)",
                        f"./container_{container_group_id}_{container_id}.json",
                        f"./container_group_{container_group_id}.json)",
                    ]
                )
            )

            # Start Container
            start_container_commands.append("crictl start $container_id")

            check_commands.append(
                f"$res=(container_exec -podName {pod_name} -containerName {container_name} -- "
                + "sh -c 'echo ContainerAlive!!; sleep 1')"
            )
            check_commands.extend(
                [
                    "if ($res -ne 'ContainerAlive!!') {",
                    f"  Write-Output 'ERROR: exec failed on {container_name}'",
                    "  $hasError = $true",
                    "}",
                ]
            )

            stop_container_commands.append(
                "; ".join(
                    [
                        f"$containerId=crictl ps --pod (crictl pods --name {pod_name} -q) --name {container_name} -q -a",
                        "if ($containerId) { crictl stop $containerId",
                        "crictl rm $containerId }",
                    ]
                )
            )

            write_script(
                f"container_exec_{container_group_id}_{container_id}.ps1",
                [
                    "param(",
                    "  [parameter(ValueFromRemainingArguments=$true)][string[]]$argv",
                    ")",
                    *run_script_common,
                    checked_container_exec_fn,
                    "if (!$argv) {",
                    "  $argv = @('bash')",
                    "}",
                    f"container_exec -podName {pod_name} -containerName {container_name} -it -- @argv",
                ],
            )

        with open(
            os.path.join(output_conf_dir, f"container_group_{container_group_id}.json"),
            "w",
            encoding="utf-8",
        ) as f:
            container_group_json = container_group_template.copy()
            container_group_json["metadata"]["name"] = pod_name
            annotations = container_group_json["annotations"]
            annotations["io.microsoft.virtualmachine.computetopology.processor.count"] = str(group_cpus)
            annotations["io.microsoft.virtualmachine.computetopology.memory.sizeinmb"] = str(group_memory * 1024)

            security_policy = (
                container_group["properties"].get("confidentialComputeProperties", {}).get("ccePolicy", "")
            )
            if not security_policy or "parameters('ccePolicies')" in security_policy:
                raise Exception("ccePolicies parameter not resolved, run c-aci-testing policies gen first")

            annotations["io.microsoft.virtualmachine.lcow.securitypolicy"] = security_policy

            json.dump(container_group_json, f, indent=2)

    write_script("pull.ps1", pull_commands)
    write_script("runp.ps1", start_pod_commands)
    write_script("startc.ps1", start_container_commands)
    write_script(
        "check.ps1",
        [
            "$hasError = $false",
            "try {",
            *check_commands,
            "} catch {",
            "  Write-Output 'ERROR: failed to run check' $_.Exception.ToString()",
            "  $hasError = $true",
            "}",
            # exit 0 is actually required to sets $LASTEXITCODE in powershell
            "if ($hasError) { exit 1 } else { exit 0 }",
        ],
    )
    write_script("stopc.ps1", stop_container_commands)
    write_script("stop.ps1", stop_pod_commands)

    write_script(
        "run.ps1",
        [
            f"cd C:\\{prefix}",
            ".\\pull.ps1",
            ".\\stop.ps1",
            ".\\runp.ps1",
            ".\\startc.ps1",
        ],
    )


def vm_runc(
    target_path: str,
    deployment_name: str,
    subscription: str,
    resource_group: str,
    managed_identity: str,
    storage_account: str,
    win_flavor: str,
    registry: str,
    repository: str,
    tag: str,
    prefix: str,
    **kwargs,
):
    lcow_config_blob_name = f"lcow_config_{deployment_name}"
    vm_name = f"{deployment_name}-vm"

    temp_dir = tempfile.mkdtemp()

    print(f"Constructing LCOW configs and scripts in {temp_dir}...")

    make_configs(
        target_path=target_path,
        subscription=subscription,
        resource_group=resource_group,
        deployment_name=deployment_name,
        win_flavor=win_flavor,
        registry=registry,
        repository=repository,
        tag=tag,
        prefix=prefix,
        output_conf_dir=temp_dir,
    )

    print(f"Uploading LCOW config and scripts to {vm_name}...")

    upload_to_vm_and_run(
        src=temp_dir,
        dst="C:\\" + prefix,
        subscription=subscription,
        resource_group=resource_group,
        vm_name=vm_name,
        storage_account=storage_account,
        container_name=VM_CONTAINER_NAME,
        blob_name=lcow_config_blob_name,
        managed_identity=managed_identity,
        commands=[f"cd C:\\{prefix}", ".\\run.ps1", 'Write-Output "run.ps1 result: $LASTEXITCODE"'],
    )

    run_on_vm(
        vm_name=vm_name,
        subscription=subscription,
        resource_group=resource_group,
        command="C:/containerplat/crictl.exe pods; C:/containerplat/crictl.exe ps -a",
    )
