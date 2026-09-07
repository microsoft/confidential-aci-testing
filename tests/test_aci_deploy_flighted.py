#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

import json

import pytest

from c_aci_testing.tools import aci_deploy_flighted
from c_aci_testing.tools.aci_deploy_flighted import (
    _inject_secrets,
    _mask_secure_parameters,
    _validate_resolved_secrets,
    _validate_template,
    _wait_for_resources,
)


def _container_group(**overrides) -> dict:
    resource = {
        "type": "Microsoft.ContainerInstance/containerGroups",
        "apiVersion": "2023-05-01",
        "name": "[deployment().name]",
        "location": "[resourceGroup().location]",
        "properties": {
            "osType": "Linux",
            "containers": [],
        },
    }
    resource.update(overrides)
    return resource


def test_validate_template_accepts_independent_container_groups():
    resources = [_container_group(), _container_group(name="second")]

    _validate_template({"resources": resources, "outputs": {}}, resources)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("condition", "[equals(parameters('enabled'), true())]"),
        ("copy", {"name": "groups", "count": 2}),
        ("scope", "/subscriptions/subscription-id"),
        ("existing", True),
        ("import", "provider"),
    ],
)
def test_validate_template_rejects_unsupported_resource_semantics(key: str, value):
    resources = [_container_group(**{key: value})]

    with pytest.raises(RuntimeError, match=key):
        _validate_template({"resources": resources}, resources)


def test_validate_template_rejects_dependencies():
    resources = [_container_group(dependsOn=["other"])]

    with pytest.raises(RuntimeError, match="dependencies"):
        _validate_template({"resources": resources}, resources)


def test_validate_template_allows_empty_dependencies():
    resources = [_container_group(dependsOn=[])]

    _validate_template({"resources": resources}, resources)


def test_validate_template_rejects_property_loops():
    resources = [
        _container_group(
            properties={
                "copy": [
                    {
                        "name": "containers",
                        "count": 2,
                        "input": {"name": "[copyIndex('containers')]"},
                    }
                ]
            }
        )
    ]

    with pytest.raises(RuntimeError, match="property loops"):
        _validate_template({"resources": resources}, resources)


def test_validate_template_rejects_non_container_group_resources():
    resources = [
        {
            "type": "Microsoft.Authorization/roleAssignments",
            "apiVersion": "2022-04-01",
            "name": "role",
        }
    ]

    with pytest.raises(RuntimeError, match="only Microsoft.ContainerInstance/containerGroups"):
        _validate_template({"resources": resources}, resources)


@pytest.mark.parametrize(
    "expression",
    [
        "[reference(resourceId('Microsoft.Storage/storageAccounts', 'account'))]",
        "[resourceInfo('Microsoft.Storage/storageAccounts', 'account')]",
        "[listKeys(resourceId('Microsoft.Storage/storageAccounts', 'account'), '2023-01-01')]",
        "[listAccountSas(resourceId('Microsoft.Storage/storageAccounts', 'account'), '2023-01-01', {})]",
    ],
)
def test_validate_template_rejects_runtime_resource_reads(expression: str):
    resources = [_container_group(properties={"value": expression})]

    with pytest.raises(RuntimeError, match=r"runtime resource reads"):
        _validate_template({"resources": resources}, resources)


def test_validate_template_rejects_runtime_resource_reads_in_outputs():
    resources = [_container_group()]
    template = {
        "resources": resources,
        "outputs": {
            "secret": {
                "type": "string",
                "value": "[listKeys(resourceId('Microsoft.Storage/storageAccounts', 'account'), '2023-01-01')]",
            }
        },
    }

    with pytest.raises(RuntimeError, match=r"listKeys"):
        _validate_template(template, resources)


def test_validate_template_rejects_runtime_resource_reads_via_variables():
    resources = [_container_group(properties={"secret": "[variables('storageKey')]"})]
    template = {
        "variables": {
            "storageKey": (
                "[listKeys(resourceId('Microsoft.Storage/storageAccounts', " "'account'), '2023-01-01').keys[0].value]"
            )
        },
        "resources": resources,
    }

    with pytest.raises(RuntimeError, match=r"listKeys"):
        _validate_template(template, resources)


def test_mask_secure_parameters_rejects_key_vault_references():
    template = {
        "parameters": {"secret": {"type": "secureString"}},
        "resources": [_container_group(properties={"secret": "[parameters('secret')]"})],
    }
    parameters = {
        "parameters": {
            "secret": {
                "reference": {
                    "keyVault": {
                        "id": "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.KeyVault/vaults/vault"
                    },
                    "secretName": "secret",
                }
            }
        }
    }

    with pytest.raises(RuntimeError, match="Key Vault references"):
        _mask_secure_parameters(template, parameters)


def test_validate_template_rejects_transformed_secure_parameters():
    resources = [
        _container_group(
            properties={
                "secret": "[base64(parameters('secret'))]",
                "direct": "[parameters('secret')]",
            }
        )
    ]
    template = {
        "parameters": {"secret": {"type": "secureString"}},
        "resources": resources,
    }

    with pytest.raises(RuntimeError, match="must be used verbatim"):
        _validate_template(template, resources)


def test_validate_template_rejects_secure_parameters_in_resource_names():
    resources = [_container_group(name="[parameters('secret')]")]
    template = {
        "parameters": {"secret": {"type": "secureString"}},
        "resources": resources,
    }

    with pytest.raises(RuntimeError, match="may only be referenced directly"):
        _validate_template(template, resources)


def test_validate_template_rejects_secure_parameters_in_outputs():
    resources = [_container_group()]
    template = {
        "parameters": {"secret": {"type": "secureString"}},
        "resources": resources,
        "outputs": {
            "secret": {
                "type": "string",
                "value": "[parameters('secret')]",
            }
        },
    }

    with pytest.raises(RuntimeError, match="may only be referenced directly"):
        _validate_template(template, resources)


def test_validate_template_rejects_secure_parameters_via_variables():
    resources = [_container_group(properties={"secret": "[variables('secretValue')]"})]
    template = {
        "parameters": {"secret": {"type": "secureString"}},
        "variables": {"secretValue": "[parameters('secret')]"},
        "resources": resources,
    }

    with pytest.raises(RuntimeError, match="may only be referenced directly"):
        _validate_template(template, resources)


def test_validate_template_rejects_secure_parameter_aliases():
    resources = [_container_group(properties={"secret": "[parameters('alias')]"})]
    template = {
        "parameters": {
            "secret": {"type": "secureString"},
            "alias": {
                "type": "string",
                "defaultValue": "[parameters('secret')]",
            },
        },
        "resources": resources,
    }

    with pytest.raises(RuntimeError, match="may only be referenced directly"):
        _validate_template(template, resources)


def test_validate_template_accepts_verbatim_secure_parameters():
    resources = [_container_group(properties={"secret": "[parameters('secret')]"})]
    template = {
        "parameters": {"secret": {"type": "secureString"}},
        "resources": resources,
    }

    _validate_template(template, resources)


def test_unused_secure_parameter_does_not_require_a_direct_value():
    template = {
        "parameters": {"secret": {"type": "secureString"}},
        "resources": [_container_group()],
    }
    parameters = {
        "parameters": {
            "secret": {
                "reference": {
                    "keyVault": {
                        "id": "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.KeyVault/vaults/vault"
                    },
                    "secretName": "secret",
                }
            }
        }
    }

    masked, secrets = _mask_secure_parameters(template, parameters)

    assert masked == parameters
    assert secrets == {}


def test_secure_parameter_is_substituted_only_after_resolution():
    template = {
        "parameters": {"secret": {"type": "secureString"}},
        "resources": [_container_group(properties={"secret": "[parameters('secret')]"})],
    }
    parameters = {"parameters": {"secret": {"value": 'value with "quotes"'}}}

    masked, secrets = _mask_secure_parameters(template, parameters)
    sentinel = masked["parameters"]["secret"]["value"]
    resolved = [_container_group(properties={"secret": sentinel})]

    _validate_resolved_secrets(resolved, secrets)
    body = _inject_secrets(json.dumps(resolved[0]), secrets)

    assert 'value with \\"quotes\\"' in body
    assert sentinel not in body
    assert "value with" not in json.dumps(masked)


def test_secure_parameter_sentinel_does_not_collide_with_template_literals(monkeypatch):
    template = {
        "parameters": {"secret": {"type": "secureString"}},
        "resources": [
            _container_group(
                properties={
                    "secret": "[parameters('secret')]",
                    "literal": "__caci_secret_collision__",
                }
            )
        ],
    }
    parameters = {"parameters": {"secret": {"value": "real-secret"}}}
    tokens = iter(("collision", "unique"))
    monkeypatch.setattr(aci_deploy_flighted.secrets_module, "token_hex", lambda _: next(tokens))

    masked, secrets = _mask_secure_parameters(template, parameters)
    sentinel = masked["parameters"]["secret"]["value"]
    resolved = [
        _container_group(
            properties={
                "secret": sentinel,
                "literal": "__caci_secret_collision__",
            }
        )
    ]

    body = _inject_secrets(json.dumps(resolved[0]), secrets)

    assert sentinel == "__caci_secret_unique__"
    assert json.loads(body)["properties"] == {
        "secret": "real-secret",
        "literal": "__caci_secret_collision__",
    }


def test_transformed_secure_parameter_fails_closed():
    template = {
        "parameters": {"secret": {"type": "secureString"}},
        "resources": [_container_group(properties={"secret": "[parameters('secret')]"})],
    }
    parameters = {"parameters": {"secret": {"value": "real-secret"}}}
    _, secrets = _mask_secure_parameters(template, parameters)
    resolved = [_container_group(properties={"secret": "base64-result"})]

    with pytest.raises(RuntimeError, match="did not reach"):
        _validate_resolved_secrets(resolved, secrets)


class _ArmWithoutProvisioningState:
    def request(self, method: str, path: str):
        return {"properties": {}}


def test_wait_for_resources_fails_when_provisioning_state_is_missing():
    with pytest.raises(RuntimeError, match="did not include properties.provisioningState"):
        _wait_for_resources(
            [_container_group(name="group")],
            _ArmWithoutProvisioningState(),
            "subscription",
            "resource-group",
            timeout=0,
        )
