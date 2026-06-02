#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import json
import subprocess
import tarfile
import tempfile

VM_CONTAINER_NAME = "container"

def containerplat_cache_from_path(storage_account: str, container_name: str, blob_name: str, cplat_path: str):
    with open(f"{cplat_path}/deploy.json", "r+", encoding="utf-8") as f:
        data = json.load(f)
        data["Force"] = True
        data["SevSnpEnabled"] = True
        data["EnableLayerIntegrity"] = True
        data["NoLCOWGPU"] = True
        data["RuntimeOptions"][0]["ShareScratch"] = True

        # Inject the runhcs-lcow `hcl-enabled = "False"` default container
        # annotation on every cplat package, regardless of whether deploy.json
        # already has it. Without this, confidential LCOW SNP UVMs fail to
        # boot on dev cplat packages whose shim defaults `HclEnabled=true` —
        # HCS rejects the create-compute-system JSON with HCS_E_INVALID_JSON.
        # Documented gap in upstream cplat: the `DefaultContainerAnnotations`
        # block in deploy.json's RuntimeOptions is only honored by the
        # deploy.exe code path; the deploy.ps1 PS-template path renders
        # `containerd.toml` from `containerd-deploy-ps-template.toml`, which
        # hardcodes only `io.microsoft.disable-unsafe-operations = "true"`.
        # Setting it here in deploy.json covers the deploy.exe path; for
        # nodes that bootstrap via deploy.ps1, the operator must also patch
        # the PS template (see Parma-Azure/cplat/Apply-CplatCustomizations
        # `unified` mode).
        for runtime in data.get("RuntimeOptions", []):
            if runtime.get("Name") == "runhcs-lcow":
                annotations = runtime.setdefault("DefaultContainerAnnotations", {})
                annotations.setdefault(
                    "io.microsoft.virtualmachine.lcow.hcl-enabled", "False"
                )

        f.seek(0)
        json.dump(data, f, indent=4)
        f.truncate()

    tar_path = tempfile.mktemp(".tar", "cplat-")

    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(cplat_path, arcname="containerplat_build")

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
            tar_path,
            "--auth-mode",
            "login",
            "--overwrite",
        ],
        check=True,
    )


def containerplat_cache_from_ado(
    storage_account: str, container_name: str, blob_name: str, cplat_feed: str, cplat_name: str, cplat_version: str
):
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
                cplat_feed,
                "--name",
                cplat_name,
                "--version",
                cplat_version,
                "--path",
                temp_dir,
            ],
            check=True,
        )

        containerplat_cache_from_path(storage_account, container_name, blob_name, temp_dir)


def containerplat_cache(
    cplat_blob_name: str,
    storage_account: str,
    container_name: str,
    cplat_feed: str,
    cplat_name: str,
    cplat_version: str,
    cplat_path: str,
):
    if cplat_path:
        print(f"Updating deploy.json and uploading containerplat in {cplat_path}")
        containerplat_cache_from_path(
            storage_account=storage_account,
            container_name=container_name,
            blob_name=cplat_blob_name,
            cplat_path=cplat_path,
        )
    elif cplat_feed or cplat_name or cplat_version:
        if not cplat_feed or not cplat_name or not cplat_version:
            raise Exception("Missing cplat_feed, cplat_name, or cplat_version (all must be set or all must be empty)")

        print(f"Downloading containerplat from ADO {cplat_feed}: {cplat_name} {cplat_version}")
        containerplat_cache_from_ado(
            storage_account=storage_account,
            container_name=container_name,
            blob_name=cplat_blob_name,
            cplat_feed=cplat_feed,
            cplat_name=cplat_name,
            cplat_version=cplat_version,
        )
    else:
        raise Exception("Missing cplat_path or cplat_feed, cplat_name, cplat_version")


def vm_cache_cplat(
    cplat_blob_name: str,
    storage_account: str,
    cplat_feed: str,
    cplat_name: str,
    cplat_version: str,
    cplat_path: str,
    **kwargs,
):
    containerplat_cache(
        cplat_blob_name=cplat_blob_name,
        storage_account=storage_account,
        container_name=VM_CONTAINER_NAME,
        cplat_feed=cplat_feed,
        cplat_name=cplat_name,
        cplat_version=cplat_version,
        cplat_path=cplat_path,
    )
