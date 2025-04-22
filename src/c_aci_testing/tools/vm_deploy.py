#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

from .vm_create import vm_create
from .vm_runc import vm_runc


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
    use_official_images: bool,
    official_image_sku: str,
    official_image_version: str,
    vm_image: str,
    win_flavor: str,
    cplat_feed: str,
    cplat_name: str,
    cplat_version: str,
    cplat_blob_name: str,
    cplat_path: str,
    storage_account: str,
    vm_size: str,
    prefix: str,
    vm_zone: str,
    resource_tags: dict[str, str],
    **kwargs,
):
    """
    :param cplat_feed: ADO feed name for containerplat, can be empty to use existing cache
    :param cplat_name: Name of the containerplat package, can be empty
    :param cplat_version: Version of the containerplat package, can be empty
    :param cplat_blob_name: Name to use for the containerplat blob, can be empty for per-deployment blobs
    """

    vm_create(
        deployment_name=deployment_name,
        subscription=subscription,
        resource_group=resource_group,
        location=location,
        managed_identity=managed_identity,
        use_official_images=use_official_images,
        official_image_sku=official_image_sku,
        official_image_version=official_image_version,
        vm_image=vm_image,
        win_flavor=win_flavor,
        cplat_feed=cplat_feed,
        cplat_name=cplat_name,
        cplat_version=cplat_version,
        cplat_path=cplat_path,
        cplat_blob_name=cplat_blob_name,
        storage_account=storage_account,
        vm_size=vm_size,
        vm_zone=vm_zone,
        resource_tags=resource_tags,
    )

    vm_runc(
        target_path=target_path,
        deployment_name=deployment_name,
        subscription=subscription,
        resource_group=resource_group,
        managed_identity=managed_identity,
        storage_account=storage_account,
        win_flavor=win_flavor,
        registry=registry,
        repository=repository,
        tag=tag,
        prefix=prefix,
    )
