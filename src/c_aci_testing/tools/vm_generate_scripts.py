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
from c_aci_testing.utils.vm import resolve_manifest_hash

MOUNTHOST_IMAGE = "mcr.microsoft.com/aci/virtual-node-2-mount-host:main_20260116.1"
AZURE_FILE_VOLUME_HOST_PATH_PREFIX = "sandbox:///tmp/atlas/azureFileVolume"


def _arm_container_to_cri(container, volume_info):
    """
    Convert an ARM container definition to a partial CRI container config dict.
    Returns (cri_fields, is_privileged) where cri_fields has keys like
    "image", "command", "envs", "mounts", "privileged".
    """
    props = container["properties"]
    cri = {}

    if "command" in props:
        cri["command"] = props["command"]
    if "environmentVariables" in props:
        cri["envs"] = [{"key": env["name"], "value": env["value"]} for env in props["environmentVariables"]]

    is_privileged = False
    if "securityContext" in props:
        if props["securityContext"].get("privileged", False):
            is_privileged = True

    # Volume mounts
    if "volumeMounts" in props:
        mounts = []
        for vm in props["volumeMounts"]:
            vol = volume_info.get(vm["name"])
            if vol is None:
                raise Exception(f"Volume '{vm['name']}' referenced in volumeMount but not defined in volumes")
            if vol["type"] == "emptyDir":
                mounts.append(
                    {
                        "container_path": vm["mountPath"],
                        "host_path": f"{AZURE_FILE_VOLUME_HOST_PATH_PREFIX}/{vm['name']}",
                        "propagation": 2,  # PROPAGATION_BIDIRECTIONAL
                    }
                )
            elif vol["type"] == "azureFile":
                mounts.append(
                    {
                        "container_path": vm["mountPath"],
                        "host_path": f"{AZURE_FILE_VOLUME_HOST_PATH_PREFIX}/{vm['name']}/mnt",
                        "propagation": 1,  # PROPAGATION_HOST_TO_CONTAINER
                    }
                )
        if mounts:
            cri["mounts"] = mounts

    return cri, is_privileged


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
    no_resolve_manifest_hash: bool = False,
):
    print(f"Constructing LCOW configs and scripts in {output_conf_dir}...")

    bicep_file_path, _ = find_bicep_files(target_path)

    templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    lcow_config_dir = os.path.join(templates_dir, "lcow_configs")
    wcow_config_dir = os.path.join(templates_dir, "wcow_configs")

    def write_script(file, script):
        with open(os.path.join(output_conf_dir, file), "w", encoding="utf-8") as f:
            f.write("\r\n".join(script))

    with open(os.path.join(templates_dir, "common.ps1"), "rt", encoding="utf-8") as f:
        write_script("common.ps1", [l.rstrip() for l in f.readlines()])

    script_head = [
        "cd (Split-Path -Parent ($MyInvocation.MyCommand.Path))",
        ". .\\common.ps1",
    ]

    pull_commands = script_head.copy()
    start_pod_commands = script_head.copy()
    create_container_commands = script_head.copy()
    start_container_commands = script_head.copy()
    check_commands = script_head.copy()
    stop_container_commands = script_head.copy()
    stop_pod_commands = script_head.copy()
    need_acr_pull = False

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

    # WCOW templates — loaded once, selected per-CG by osType detection in the
    # loop below. WCOW and LCOW configs are different shapes: WCOW
    # container.json has no `linux.security_context`, and WCOW container_group
    # uses `wcow.isolation_type`/`writable_efi`/`enforcer` annotations and the
    # `io.microsoft.virtualmachine.wcow.securitypolicy` annotation.
    with open(
        os.path.join(wcow_config_dir, "container.json.template"),
        encoding="utf-8",
    ) as wcow_container_template_file:
        wcow_container_template = json.load(wcow_container_template_file)

    with open(
        os.path.join(wcow_config_dir, "container_group.json.template"),
        encoding="utf-8",
    ) as wcow_container_group_template_file:
        wcow_container_group_template = json.load(wcow_container_group_template_file)

    if win_flavor == "ws2022":
        del container_group_template["annotations"]["io.microsoft.virtualmachine.lcow.hcl-enabled"]

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

    cgs = list(arm_template_for_each_container_group(arm_template_json))
    single_pod = len(cgs) <= 1
    for container_group, containers in cgs:
        # Detect osType per CG: Windows triggers the confidential WCOW path
        # (different runtime, templates, security-policy annotation, and
        # health-check strategy than confidential LCOW).
        os_type = container_group.get("properties", {}).get("osType", "Linux")
        is_wcow = isinstance(os_type, str) and os_type.lower() == "windows"
        cg_runtime = "runhcs-wcow-hypervisor" if is_wcow else "runhcs-lcow"
        cg_container_template = wcow_container_template if is_wcow else container_template
        cg_container_group_template = (
            wcow_container_group_template if is_wcow else container_group_template
        )
        cg_securitypolicy_annotation = (
            "io.microsoft.virtualmachine.wcow.securitypolicy"
            if is_wcow
            else "io.microsoft.virtualmachine.lcow.securitypolicy"
        )

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
        if single_pod:
            pod_name = prefix
        pod_json_file = f"pod_{container_group_id}.snp.json"
        if single_pod:
            pod_json_file = "pod.snp.json"

        start_pod_commands.append(f"$group_id = (azcrictl runp --runtime {cg_runtime} {pod_json_file})")
        start_pod_commands.append(f"Write-Output 'Started pod {pod_name} with ID: ' $group_id")

        shimdiag_exec_pod = f'shimdiag_exec_pod -podName "{pod_name}" --'

        # dmesg streaming is LCOW-only: confidential WCOW UVMs don't expose
        # a Linux-style dmesg ring through shimdiag. Skipping keeps the WCOW
        # runp output clean.
        if not is_wcow:
            write_script(
                f"stream_dmesg_{container_group_id}.ps1",
                [
                    *script_head,
                    f"echo '-------- pod {pod_name} started --------' >> dmesg_{container_group_id}.log",
                    f"{shimdiag_exec_pod} dmesg -w >> dmesg_{container_group_id}.log",
                    "if (-not $?) {",
                    f"  {shimdiag_exec_pod} cat /dev/kmsg >> dmesg_{container_group_id}.log",
                    "}",
                ],
            )

            start_pod_commands.append(
                f"Start-Process powershell -WorkingDirectory . -ArgumentList /c,.\\stream_dmesg_{container_group_id}.ps1"
            )

        if is_wcow:
            # Confidential WCOW: after a pod is stopped/removed, containerd
            # needs time to release the UVM and shim resources before another
            # pod can be created on the same VM; a 3rd+ pod created in quick
            # succession otherwise hits "container exited unexpectedly". Wait
            # for THIS pod to drain (matched by name) rather than clearing
            # every pod on the VM, so parallel pods are left untouched.
            stop_pod_commands.append(f"$podId = (get_pod_id -NoError {pod_name})")
            stop_pod_commands.append("if ($podId) {")
            stop_pod_commands.append("  azcrictl stopp $podId; azcrictl rmp $podId")
            stop_pod_commands.append("  $deadline = (Get-Date).AddSeconds(60)")
            stop_pod_commands.append(f"  while ((Get-Date) -lt $deadline -and (get_pod_id -NoError {pod_name})) {{")
            stop_pod_commands.append(f"    Write-Output 'Waiting for pod {pod_name} to drain...'")
            stop_pod_commands.append("    Start-Sleep -Seconds 3")
            stop_pod_commands.append("  }")
            stop_pod_commands.append("  Start-Sleep -Seconds 5")
            stop_pod_commands.append("}")
        else:
            stop_pod_commands.append(
                f"$podId = (get_pod_id -NoError {pod_name}); if ($podId) {{ azcrictl stopp $podId; azcrictl rmp $podId }}"
            )

        connect_script_name = f"connect_{container_group_id}.ps1"
        if single_pod:
            connect_script_name = "connect.ps1"
        write_script(
            connect_script_name,
            [
                "param(",
                "  [parameter(ValueFromRemainingArguments=$true)][string[]]$argv",
                ")",
                *script_head,
                "if (!$argv) {",
                f"  $argv = @('{'cmd' if is_wcow else 'bash'}')",
                "}",
                f"shimdiag_exec_pod -podName '{pod_name}' -t -- @argv",
            ],
        )

        # Pod-level smoke check.
        if is_wcow:
            # Confidential WCOW exec checks are unreliable as a smoke test:
            # - short-lived containers exit before the exec can run
            #   ("must be running to create additional execs").
            # - shimdiag/crictl exec PATH inheritance in WCOW is flaky.
            # Replace with a state-based check: verify the pod exists. The
            # workflow's per-workload output check is the real signal.
            check_commands.append(f"if (-not (get_pod_id -NoError {pod_name})) {{")
            check_commands.extend(
                [
                    f"  Write-Output 'ERROR: pod {pod_name} not found'",
                    "  $hasError = $true",
                    "}",
                ]
            )
        else:
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

        containers = list(containers)

        # Build volume info map from ARM volumes
        arm_volumes = container_group["properties"].get("volumes", [])
        volume_info = {}  # name -> {"type": "emptyDir"|"azureFile", ...}
        for vol in arm_volumes:
            if "emptyDir" in vol:
                volume_info[vol["name"]] = {"type": "emptyDir"}
            elif "azureFile" in vol:
                volume_info[vol["name"]] = {
                    "type": "azureFile",
                    "shareName": vol["azureFile"]["shareName"],
                    "storageAccountName": vol["azureFile"]["storageAccountName"],
                    "storageAccountKey": vol["azureFile"].get("storageAccountKey", ""),
                }
            else:
                raise Exception(
                    f"Unsupported volume type for volume '{vol['name']}': only emptyDir and azureFile are supported"
                )

        # Synthesize mounthost sidecar containers for azureFile volumes
        azure_file_volumes = {name: info for name, info in volume_info.items() if info["type"] == "azureFile"}
        single_container = (len(containers) + len(azure_file_volumes)) <= 1

        def emit_container(image, container_id, cri_fields, is_privileged, cpu, memory_gb):
            nonlocal need_acr_pull, has_privileged_containers, group_cpus, group_memory, pod_json_file

            if not no_resolve_manifest_hash:
                orig_image = image
                image = resolve_manifest_hash(image, "linux/amd64" if not is_wcow else "windows/amd64")
                print(f"Resolved {orig_image} to {image}")

            is_acr_image = registry.endswith(".azurecr.io") and image.startswith(registry)

            if is_acr_image and not need_acr_pull:
                pull_commands.append(". .\\_acr_pull.ps1")
                need_acr_pull = True

            pull_commands.append(
                f'if (-not ((azcrictl images -o json | ConvertFrom-Json).images |? {{$_.repoTags.Contains("{image}")}})) {{'
            )
            if is_acr_image:
                pull_commands.append(f"  Pull-Image {pod_json_file} {image}")
            else:
                pull_commands.append(f"  azcrictl pull --pod-config {pod_json_file} {image}")
            pull_commands.append("}")

            container_name = f"{prefix}_{container_group_id}_{container_id}"
            group_cpus += cpu
            group_memory += memory_gb

            container_json_file = f"container_{container_group_id}_{container_id}.json"
            if single_pod and single_container:
                container_json_file = "container.json"
            elif single_pod:
                container_json_file = f"container_{container_id}.json"

            if is_privileged:
                if is_wcow:
                    # Confidential WCOW handles "privileged" via policy
                    # (`allow_elevated: true` per-container rego), not via
                    # the LCOW `linux.security_context.privileged` field —
                    # which doesn't exist in the WCOW container.json shape.
                    raise Exception(
                        f"Container '{container_name}' is marked privileged on a Windows CG. "
                        f"Set `allow_elevated: true` in the per-container Rego policy instead."
                    )
                has_privileged_containers = True

            container_json = cg_container_template.copy()
            container_json["metadata"]["name"] = container_name
            container_json["image"]["image"] = image
            container_json.update(cri_fields)
            if is_privileged and not is_wcow:
                container_json["linux"]["security_context"]["privileged"] = True

            with open(
                os.path.join(output_conf_dir, container_json_file),
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(container_json, f, indent=2)

            # Create Container
            container_log_filename = f"container_log_{container_group_id}_{container_id}.log"
            if single_pod and single_container:
                container_log_filename = "container.log"
            elif single_pod:
                container_log_filename = f"container_{container_id}.log"

            create_container_commands.append("# Fix log_path to use correct absolute path")
            create_container_commands.append(
                f"$containerJson = Get-Content {container_json_file} | ConvertFrom-Json"
            )
            # Using .log_path raises "The property 'log_path' cannot be found on this object".
            # Using ["log_path"] raises "Unable to index into an object of type "System.Management.Automation.PSObject"."
            create_container_commands.append(
                f'Add-Member -InputObject $containerJson -NotePropertyName log_path -NotePropertyValue "$PWD\\{container_log_filename}" -Force'
            )

            create_container_commands.append(
                f'$containerJson | ConvertTo-Json -Depth 100 | Set-Content -Encoding utf8 {container_json_file}'
            )
            create_container_commands.append("")

            create_container_commands.append(
                " ".join(
                    [
                        "azcrictl create --no-pull",
                        f"(get_pod_id {pod_name})",
                        container_json_file,
                        pod_json_file,
                    ]
                )
            )

            # Start Container
            start_container_commands.append("try {")
            start_container_commands.append(
                f"  $containerId = (get_container_id {pod_name} {container_name})"
            )
            start_container_commands.append("  azcrictl start $containerId")
            start_container_commands.append(f"  Write-Output 'Started container {container_name} with ID: ' $containerId")
            start_container_commands.append("} catch {")
            start_container_commands.append(f"  Write-Error 'Container {container_name} not created yet.  Run createc.ps1.'")
            start_container_commands.append("}")

            if is_wcow:
                # See comment on pod-level WCOW check above. Short-lived
                # containers (info_cwcow runs and exits in <1s) make exec
                # checks unreliable. Use a state-based check instead.
                check_commands.append(
                    f"if (-not (get_container_id -NoError {pod_name} {container_name})) {{"
                )
                check_commands.extend(
                    [
                        f"  Write-Output 'ERROR: container {container_name} not found in pod {pod_name}'",
                        "  $hasError = $true",
                        "}",
                    ]
                )
            else:
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
                f"$containerId = (get_container_id -NoError {pod_name} {container_name}); if ($containerId) {{ azcrictl stop -t 10 $containerId; azcrictl rm $containerId }}"
            )

            container_exec_script_name = f"container_exec_{container_group_id}_{container_id}.ps1"
            if single_pod and single_container:
                container_exec_script_name = "container.ps1"
            elif single_pod:
                container_exec_script_name = f"container_{container_id}.ps1"

            write_script(
                container_exec_script_name,
                [
                    "param(",
                    "  [parameter(ValueFromRemainingArguments=$true)][string[]]$argv",
                    ")",
                    *script_head,
                    "if (!$argv) {",
                    f"  $argv = @('{'cmd' if is_wcow else 'bash'}')",
                    "}",
                    f"container_exec -podName {pod_name} -containerName {container_name} -it -- @argv",
                ],
            )

        # Emit mounthost sidecar containers for azureFile volumes
        for vol_name, vol_info in azure_file_volumes.items():
            sidecar_name = f"mounthost-{vol_name}".replace("-", "_")
            emit_container(
                image=MOUNTHOST_IMAGE,
                container_id=sidecar_name,
                cri_fields={
                    "envs": [
                        {"key": "storage_account", "value": vol_info["storageAccountName"]},
                        {"key": "share_name", "value": vol_info["shareName"]},
                        {"key": "storage_key", "value": vol_info["storageAccountKey"]},
                        {"key": "mount_point", "value": "/volumemountscratch/mnt"},
                    ],
                    "command": ["./mount_azure_fileshare_2.sh"],
                    "mounts": [
                        {
                            "container_path": "/volumemountscratch",
                            "host_path": f"{AZURE_FILE_VOLUME_HOST_PATH_PREFIX}/{vol_name}",
                            "propagation": 2,  # PROPAGATION_BIDIRECTIONAL
                        },
                    ],
                },
                is_privileged=True,
                cpu=0,
                memory_gb=0,
            )

        # Emit ARM-defined containers
        for container in containers:
            cri_fields, is_privileged = _arm_container_to_cri(container, volume_info)
            props = container["properties"]
            emit_container(
                image=props["image"],
                container_id=container["name"],
                cri_fields=cri_fields,
                is_privileged=is_privileged,
                cpu=props["resources"]["requests"]["cpu"],
                memory_gb=props["resources"]["requests"]["memoryInGB"],
            )

        with open(
            os.path.join(output_conf_dir, pod_json_file),
            "w",
            encoding="utf-8",
        ) as f:
            container_group_json = cg_container_group_template.copy()
            container_group_json["metadata"]["name"] = pod_name
            annotations = container_group_json["annotations"]
            annotations["io.microsoft.virtualmachine.computetopology.processor.count"] = str(group_cpus)
            annotations["io.microsoft.virtualmachine.computetopology.memory.sizeinmb"] = str(group_memory * 1024)

            security_policy = (
                container_group["properties"].get("confidentialComputeProperties", {}).get("ccePolicy", "")
            )
            if not security_policy or "parameters('ccePolicies')" in security_policy:
                print("WARNING: ccePolicy not found or not resolved in ARM template, assuming non-confidential")
                # WCOW templates don't carry the LCOW securitypolicy
                # annotation, so pop is safe whichever os we're on.
                annotations.pop(cg_securitypolicy_annotation, None)
            else:
                annotations[cg_securitypolicy_annotation] = security_policy

            if has_privileged_containers and not is_wcow:
                container_group_json["linux"]["security_context"]["privileged"] = True

            json.dump(container_group_json, f, indent=2)

    write_script("pull.ps1", pull_commands)
    write_script("runp.ps1", start_pod_commands)
    write_script("createc.ps1", create_container_commands)
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
            os.path.join(templates_dir, "_acr_pull.ps1"),
            "rt",
            encoding="utf-8",
        ) as acr_pull_script:
            write_script("_acr_pull.ps1", [l.rstrip() for l in acr_pull_script.readlines()])

    write_script(
        "run.ps1",
        [
            *script_head,
            ".\\pull.ps1",
            ".\\stop.ps1",
            ".\\runp.ps1",
            ".\\createc.ps1",
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
    no_resolve_manifest_hash: bool = False,
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
        no_resolve_manifest_hash=no_resolve_manifest_hash,
    )
