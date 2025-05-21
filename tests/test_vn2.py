#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import random
import tempfile
import string
import argparse
import os

from utils import set_env

from c_aci_testing.args.parameters.location import parse_location
from c_aci_testing.args.parameters.managed_identity import parse_managed_identity
from c_aci_testing.args.parameters.registry import parse_registry
from c_aci_testing.args.parameters.repository import parse_repository
from c_aci_testing.args.parameters.resource_group import parse_resource_group
from c_aci_testing.args.parameters.subscription import parse_subscription
from c_aci_testing.args.parameters.tag import parse_tag
from c_aci_testing.args.parameters.yaml_path import parse_yaml_path
from c_aci_testing.args.parameters.policy_type import parse_policy_type
from c_aci_testing.args.parameters.replicas import parse_replicas

from c_aci_testing.tools.target_create import target_create
from c_aci_testing.tools.images_build import images_build
from c_aci_testing.tools.images_push import images_push
from c_aci_testing.tools.vn2_generate_yaml import vn2_generate_yaml
from c_aci_testing.tools.vn2_policygen import vn2_policygen


def parse_args():

    parser = argparse.ArgumentParser()
    parse_subscription(parser)
    parse_resource_group(parser)
    parse_registry(parser)
    parse_repository(parser)
    parse_tag(parser)
    parse_location(parser)
    parse_managed_identity(parser)
    parse_yaml_path(parser)
    parse_policy_type(parser)
    parse_replicas(parser)
    return vars(parser.parse_known_args()[0])


def test_vn2_generate_yaml():
    set_env()
    args = parse_args()

    with tempfile.TemporaryDirectory(prefix="target_") as target_path:

        # Create the target
        target_name = "".join(random.choices(string.ascii_lowercase, k=8))
        target_create(target_path=target_path, name=target_name)

        images_build(target_path=target_path, **args)
        images_push(target_path=target_path, **args)

        vn2_generate_yaml(
            target_path=target_path,
            deployment_name=target_name,
            **args,
        )

        print("Generated YAML:")
        with open(os.path.join(target_path, f"{target_name}.yaml"), "rt") as f:
            generated_yaml = f.read()
            print(generated_yaml)

        expected = f"""\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {target_name}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: {target_name}
  template:
    metadata:
      labels:
        app: {target_name}
      annotations:
        microsoft.containerinstance.virtualnode.ccepolicy: ''
        microsoft.containerinstance.virtualnode.identity: /subscriptions/{args["subscription"]}/resourceGroups/{args["resource_group"]}/providers/Microsoft.ManagedIdentity/userAssignedIdentities/{args["managed_identity"]}
    spec:
      containers:
      - name: primary
        image: {args["registry"]}/{target_name}/primary:latest
        resources:
          requests:
            cpu: 1
            memory: 4G
        ports:
        - containerPort: 80
      nodeSelector:
        virtualization: virtualnode2
      tolerations:
      - key: virtual-kubelet.io/provider
        operator: Exists
        effect: NoSchedule
      imagePullSecrets:
      - name: acr-auth-cacitesting
---
apiVersion: v1
kind: Service
metadata:
  name: {target_name}
  annotations:
    external-dns.alpha.kubernetes.io/hostname: {target_name}.azure.net
    external-dns.alpha.kubernetes.io/internal-hostname: clusterip.{target_name}.azure.net
spec:
  type: LoadBalancer
  ports:
  - port: 80
  selector:
    app: {target_name}
"""

        assert expected in generated_yaml

        vn2_policygen(
            target_path=target_path,
            **args,
        )
