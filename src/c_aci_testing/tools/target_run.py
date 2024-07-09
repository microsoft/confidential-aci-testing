#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import subprocess
from contextlib import contextmanager

from .aci_deploy import aci_deploy
from .aci_get_ids import aci_get_ids
from .aci_get_is_live import aci_get_is_live
from .aci_monitor import aci_monitor
from .aci_remove import aci_remove
from .images_build import images_build
from .images_pull import images_pull
from .images_push import images_push
from .policies_gen import policies_gen


@contextmanager
def target_run_ctx(
    target_path: str,
    deployment_name: str,
    subscription: str,
    resource_group: str,
    registry: str,
    repository: str | None,
    tag: str | None,
    location: str,
    managed_identity: str,
    policy_type: str = "generated",
    follow: bool = True,
    cleanup: bool = True,
    prefer_pull: bool = False,
    **kwargs,
):
    aci_ids = aci_get_ids(
        deployment_name=deployment_name,
        subscription=subscription,
        resource_group=resource_group,
    )

    if not aci_get_is_live(
        deployment_name=deployment_name,
        subscription=subscription,
        resource_group=resource_group,
        aci_ids=aci_ids,
    ):
        unpulled_services = []
        if prefer_pull:
            unpulled_services = images_pull(
                target_path=target_path,
                registry=registry,
                repository=repository,
                tag=tag,
            )
        if not prefer_pull or unpulled_services:
            images_build(
                target_path=target_path,
                registry=registry,
                repository=repository,
                tag=tag,
                services=unpulled_services,
            )
            subprocess.run(["docker", "image", "list"])
            images_push(
                target_path=target_path,
                registry=registry,
                repository=repository,
                tag=tag,
            )
        policies_gen(
            target_path=target_path,
            deployment_name=deployment_name,
            subscription=subscription,
            resource_group=resource_group,
            registry=registry,
            repository=repository,
            tag=tag,
            policy_type=policy_type,
        )
        aci_ids = aci_deploy(
            target_path=target_path,
            deployment_name=deployment_name,
            subscription=subscription,
            resource_group=resource_group,
            location=location,
            managed_identity=managed_identity,
        )

    try:
        try:
            yield aci_ids
        except Exception:
            return  # Don't remove the ACI if there was an error
        aci_monitor(
            deployment_name=deployment_name,
            subscription=subscription,
            resource_group=resource_group,
            follow=follow,
        )
    finally:
        if cleanup:
            aci_remove(
                deployment_name=deployment_name,
                subscription=subscription,
                resource_group=resource_group,
            )


def target_run(**kwargs):
    with target_run_ctx(**kwargs):
        ...
