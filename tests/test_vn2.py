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
        microsoft.containerinstance.virtualnode.injectdns: 'false'
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


def test_vn2_generate_yaml_ignore_vnets():
    """Test that ignore_vnets parameter correctly controls subnet annotation generation."""
    set_env()
    args = parse_args()

    # Test constants
    SUBNET_ANNOTATION_KEY = "microsoft.containerinstance.virtualnode.subnets.primary"
    TEST_VNET_NAME = "test-vnet"
    TEST_SUBNET_NAME = "test-subnet"

    with tempfile.TemporaryDirectory(prefix="target_") as target_path:

        # Create the target
        target_name = "".join(random.choices(string.ascii_lowercase, k=8))
        target_create(target_path=target_path, name=target_name)

        # Modify the Bicep template to include subnetIds
        bicep_path = os.path.join(target_path, f"{target_name}.bicep")
        with open(bicep_path, "rt") as f:
            bicep_content = f.read()

        # Add subnetIds to the Bicep template properties
        # Insert after osType to ensure proper placement
        bicep_content = bicep_content.replace(
            "    osType: 'Linux'",
            f"""    osType: 'Linux'
    subnetIds: [
      {{
        id: '/subscriptions/${{subscription().subscriptionId}}/resourceGroups/${{resourceGroup().name}}/providers/Microsoft.Network/virtualNetworks/{TEST_VNET_NAME}/subnets/{TEST_SUBNET_NAME}'
      }}
    ]"""
        )

        with open(bicep_path, "wt") as f:
            f.write(bicep_content)

        images_build(target_path=target_path, **args)
        images_push(target_path=target_path, **args)

        # Test 1: Generate YAML with ignore_vnets=True
        yaml_path_ignore = os.path.join(target_path, f"{target_name}_ignore.yaml")
        vn2_generate_yaml(
            target_path=target_path,
            deployment_name=target_name,
            yaml_path=yaml_path_ignore,
            ignore_vnets=True,
            **args,
        )

        print("Generated YAML with ignore_vnets=True:")
        with open(yaml_path_ignore, "rt") as f:
            generated_yaml_ignore = f.read()
            print(generated_yaml_ignore)

        # Verify that subnet annotation is NOT present when ignore_vnets=True
        assert SUBNET_ANNOTATION_KEY not in generated_yaml_ignore, \
            "Subnet annotation should not be present when ignore_vnets=True"

        # Test 2: Generate YAML with ignore_vnets=False
        yaml_path_include = os.path.join(target_path, f"{target_name}_include.yaml")
        vn2_generate_yaml(
            target_path=target_path,
            deployment_name=target_name,
            yaml_path=yaml_path_include,
            ignore_vnets=False,
            **args,
        )

        print("Generated YAML with ignore_vnets=False:")
        with open(yaml_path_include, "rt") as f:
            generated_yaml_include = f.read()
            print(generated_yaml_include)

        # Verify that subnet annotation IS present when ignore_vnets=False
        assert SUBNET_ANNOTATION_KEY in generated_yaml_include, \
            "Subnet annotation should be present when ignore_vnets=False"

        # Verify the subnet ID is correctly included
        expected_subnet_id = (
            f"/subscriptions/{args['subscription']}"
            f"/resourceGroups/{args['resource_group']}"
            f"/providers/Microsoft.Network/virtualNetworks/{TEST_VNET_NAME}"
            f"/subnets/{TEST_SUBNET_NAME}"
        )
        assert expected_subnet_id in generated_yaml_include, \
            "Correct subnet ID should be present in the annotation"
