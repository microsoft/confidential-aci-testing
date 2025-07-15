#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import json
import os
import pathlib

from c_aci_testing.utils.parse_bicep import parse_bicep, arm_template_for_each_container_group
from c_aci_testing.utils.find_bicep import find_bicep_files


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
    print(f"Constructing LCOW configs and scripts in {output_conf_dir}...")

    bicep_file_path, _ = find_bicep_files(target_path)

    lcow_config_dir = os.path.join(os.path.dirname(__file__), "..", "templates", "lcow_configs")

    def write_script(file, script):
        with open(os.path.join(output_conf_dir, file), "w", encoding="utf-8") as f:
            f.write("\r\n".join(script))

    write_script(
        "common.ps1",
        [
            r"Set-Alias -Name crictl -Value C:\ContainerPlat\crictl.exe",
            "Set-Alias -Name shimdiag -Value C:\\ContainerPlat\\shimdiag.exe",
            "",
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
            "",
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
            "",
            "cd (Split-Path -Parent ($MyInvocation.MyCommand.Path))",
        ],
    )

    script_head = [
        "cd (Split-Path -Parent ($MyInvocation.MyCommand.Path))",
        ". .\\common.ps1",
    ]

    pull_commands = script_head.copy()
    start_pod_commands = script_head.copy()
    start_container_commands = script_head.copy()
    check_commands = script_head.copy()
    stop_container_commands = script_head.copy()
    stop_pod_commands = script_head.copy()
    need_acr_pull = False

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

    arm_template_json = parse_bicep(
        target_path,
        subscription,
        resource_group,
        deployment_name,
        registry,
        repository,
        tag,
    )

    has_privileged_containers = False

    for container_group, containers in arm_template_for_each_container_group(arm_template_json):
        # Derive container group ID
        container_group_id = (
            container_group["name"]
            .replace(
                deployment_name,
                pathlib.Path(bicep_file_path).stem,
            )
            .replace("-", "_")
        )

        group_cpus = 0
        group_memory = 0

        pod_name = f"{prefix}_{container_group_id}"

        start_pod_commands.append(
            " ".join(
                [
                    "$group_id = (crictl runp",
                    "--runtime runhcs-lcow",
                    f"./pod_{container_group_id}.json)",
                ]
            )
        )

        shimdiag_exec_pod = f'shimdiag_exec_pod -podName "{pod_name}" --'

        write_script(
            f"stream_dmesg_{container_group_id}.ps1",
            [
                *script_head,
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
                *script_head,
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
            image = container["properties"]["image"]

            pull_commands.append(
                f'if (-not ((crictl images -o json | ConvertFrom-Json).images |? {{$_.repoTags.Contains("{image}")}})) {{'
            )
            if registry.endswith(".azurecr.io") and image.startswith(registry):
                need_acr_pull = True
                pull_commands.append(
                    "  "
                    + " ".join(
                        [
                            ".\\acr_pull.ps1",
                            registry,
                            ".\\pull.json",
                            "(Get-Content -Raw C:\\managed_identity_client_id.txt)",
                            image,
                        ]
                    )
                )
            else:
                pull_commands.append(
                    "  "
                    + " ".join(
                        [
                            "crictl pull",
                            "--pod-config ./pull.json",
                            container["properties"]["image"],
                        ]
                    )
                )
            pull_commands.append("}")

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
                if "securityContext" in container["properties"]:
                    container_sec_ctx = container["properties"]["securityContext"]
                    if container_sec_ctx.get("privileged", False):
                        container_json["linux"]["security_context"]["privileged"] = True
                        has_privileged_containers = True
                json.dump(container_json, f, indent=2)

            # Create Container
            start_container_commands.append(
                " ".join(
                    [
                        "$container_id = (crictl create --no-pull",
                        f"(crictl pods --name {pod_name} -q)",
                        f"./container_{container_group_id}_{container_id}.json",
                        f"./pod_{container_group_id}.json)",
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
                    *script_head,
                    "if (!$argv) {",
                    "  $argv = @('bash')",
                    "}",
                    f"container_exec -podName {pod_name} -containerName {container_name} -it -- @argv",
                ],
            )

        with open(
            os.path.join(output_conf_dir, f"pod_{container_group_id}.json"),
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

            if has_privileged_containers:
                container_group_json["linux"]["security_context"]["privileged"] = True

            json.dump(container_group_json, f, indent=2)

    write_script("pull.ps1", pull_commands)
    write_script("runp.ps1", start_pod_commands)
    write_script("startc.ps1", start_container_commands)
    write_script(
        "check.ps1",
        [
            "$hasError = $false",
            "try {",
            *[f"  {line}" for line in check_commands],
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

    if need_acr_pull:
        with open(
            os.path.join(os.path.dirname(__file__), "..", "templates", "acr_pull.ps1"),
            "rt",
            encoding="utf-8",
        ) as acr_pull_script:
            write_script("acr_pull.ps1", [l.rstrip() for l in acr_pull_script.readlines()])

    write_script(
        "run.ps1",
        [
            *script_head,
            ".\\pull.ps1",
            ".\\stop.ps1",
            ".\\runp.ps1",
            ".\\startc.ps1",
            ".\\check.ps1",
        ],
    )


def vm_generate_scripts(
    target_path: str,
    output_dir: str,
    subscription: str,
    resource_group: str,
    win_flavor: str,
    registry: str,
    repository: str,
    tag: str,
    prefix: str,
    **kwargs,
):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    make_configs(
        target_path=target_path,
        subscription=subscription,
        resource_group=resource_group,
        deployment_name="temp-deployment",
        win_flavor=win_flavor,
        registry=registry,
        repository=repository,
        tag=tag,
        prefix=prefix,
        output_conf_dir=output_dir,
    )
