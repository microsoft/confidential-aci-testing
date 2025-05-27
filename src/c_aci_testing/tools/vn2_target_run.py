#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

from contextlib import contextmanager

from .vn2_generate_yaml import vn2_generate_yaml
from .vn2_deploy import vn2_deploy
from .vn2_logs import vn2_logs
from .vn2_remove import vn2_remove
from .images_build import images_build
from .images_pull import images_pull
from .images_push import images_push
from .vn2_policygen import vn2_policygen


@contextmanager
def vn2_target_run_ctx(
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
    follow: bool = False,
    cleanup: bool = True,
    prefer_pull: bool = False,
    replicas: int = 1,
    monitor_duration_secs: int = 60,
    **kwargs,
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
        images_push(
            target_path=target_path,
            registry=registry,
            repository=repository,
            tag=tag,
        )
    vn2_generate_yaml(
        target_path=target_path,
        yaml_path="",
        subscription=subscription,
        resource_group=resource_group,
        deployment_name=deployment_name,
        managed_identity=managed_identity,
        registry=registry,
        repository=repository,
        tag=tag,
        replicas=replicas,
    )
    vn2_policygen(
        target_path=target_path,
        yaml_path="",
        policy_type=policy_type,
    )
    vn2_deploy(
        target_path=target_path,
        yaml_path="",
        monitor_duration_secs=monitor_duration_secs,
        deploy_output_file=""
    )

    error = None
    try:
        try:
            yield
        except Exception as e:
            cleanup = False
            error = e
        vn2_logs(
            deployment_name=deployment_name,
            follow=follow,
        )
    finally:
        if cleanup:
            vn2_remove(
                deployment_name=deployment_name,
            )
        if error:
            raise error


def vn2_target_run(**kwargs):
    with vn2_target_run_ctx(**kwargs):
        ...
