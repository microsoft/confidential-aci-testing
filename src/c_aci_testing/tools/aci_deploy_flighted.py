#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

"""Deploy a bicep target while sending ACI flight headers.

ARM does not forward client request headers into the resource PUTs it performs on
behalf of a template deployment, so a flighted request cannot go through
`az deployment group create`. Rather than making callers hand-write JSON request
bodies, this module keeps bicep as the source of truth and resolves it with ARM
itself:

  1. compile the bicep target to an ARM template,
  2. deploy a copy of that template with every resource moved into an `outputs`
     block - ARM evaluates all template expressions but creates nothing,
  3. PUT each fully resolved resource body directly, with the flight header.

Step 2 also keeps the target's own outputs (such as `ids`) and creates a real
deployment record under the same name, so `aci monitor`, `aci get ids` and the
`--deploy-output-file` contract behave exactly as they do for a normal deployment.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time

RESOLVED_RESOURCES_OUTPUT = "caciResolvedResources"
FLIGHT_HEADER = "x-ms-aci-merge-flights"
ACI_PROVIDER = "microsoft.containerinstance"
TERMINAL_STATES = ("Succeeded", "Failed", "Canceled")

# Template properties that describe the resource to ARM rather than forming part of
# the resource body sent to the provider.
NON_BODY_KEYS = (
    "type",
    "apiVersion",
    "name",
    "dependsOn",
    "condition",
    "copy",
    "scope",
    "existing",
    "import",
    "metadata",
)

# ARM functions that read state from a resource the template itself creates, which
# cannot be evaluated before that resource exists. Functions such as listKeys() are
# deliberately not included: against a pre-existing resource they resolve correctly
# in an outputs block, and the resolver deployment below is a real deployment.
RUNTIME_FUNCTIONS = ("reference(", "resourceInfo(")


def _run(command: list[str], what: str) -> str:
    res = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode != 0:
        detail = res.stderr.strip() or res.stdout.strip()
        raise RuntimeError(f"{what} failed: {detail}")
    return res.stdout


def compile_bicep(bicep_file_path: str) -> dict:
    return json.loads(
        _run(
            ["az", "bicep", "build", "--file", bicep_file_path, "--stdout"],
            f"Compiling {os.path.basename(bicep_file_path)}",
        )
    )


def compile_bicepparam(bicepparam_file_path: str) -> dict:
    compiled = json.loads(
        _run(
            ["az", "bicep", "build-params", "--file", bicepparam_file_path, "--stdout"],
            f"Compiling {os.path.basename(bicepparam_file_path)}",
        )
    )
    # build-params emits the parameters file either directly or wrapped in a
    # parametersJson string depending on the CLI version.
    if "parametersJson" in compiled:
        compiled = json.loads(compiled["parametersJson"])
    return compiled


def _resource_list(template: dict) -> list[dict]:
    resources = template.get("resources") or []
    # Templates using languageVersion 2.0 key resources by symbolic name.
    if isinstance(resources, dict):
        return list(resources.values())
    return list(resources)


def _find_runtime_references(node) -> list[str]:
    found: list[str] = []

    def walk(value):
        if isinstance(value, str):
            if value.startswith("[") and any(fn in value for fn in RUNTIME_FUNCTIONS):
                found.append(value)
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(node)
    return found


def _build_resolver_template(template: dict, resources: list[dict]) -> dict:
    resolver = json.loads(json.dumps(template))
    resolver["resources"] = {} if isinstance(template.get("resources"), dict) else []
    outputs = dict(resolver.get("outputs") or {})
    outputs[RESOLVED_RESOURCES_OUTPUT] = {"type": "array", "value": resources}
    resolver["outputs"] = outputs
    return resolver


def _resource_url(subscription: str, resource_group: str, resource: dict) -> str:
    resource_type = resource["type"]
    name = str(resource["name"])
    api_version = resource["apiVersion"]

    type_parts = resource_type.split("/")
    provider, child_types = type_parts[0], type_parts[1:]
    name_parts = name.split("/")

    if len(child_types) != len(name_parts):
        raise RuntimeError(
            f"Cannot build a resource URL for type '{resource_type}' with name '{name}'"
        )

    path = "/".join(f"{t}/{n}" for t, n in zip(child_types, name_parts))
    return (
        f"/subscriptions/{subscription}/resourceGroups/{resource_group}"
        f"/providers/{provider}/{path}?api-version={api_version}"
    )


def _resource_body(resource: dict) -> dict:
    return {k: v for k, v in resource.items() if k not in NON_BODY_KEYS}


def _secure_parameter_names(template: dict) -> set[str]:
    declared = template.get("parameters") or {}
    return {
        name
        for name, spec in declared.items()
        if str((spec or {}).get("type", "")).lower() in ("securestring", "secureobject")
    }


def _mask_secure_parameters(template: dict, parameters: dict) -> tuple[dict, dict[str, str]]:
    """Swap secure parameter values for sentinels before the resolver deployment.

    The resolver's outputs are persisted on the deployment record, so a secret
    reaching them would be readable by anyone with read access to the resource
    group long after the run. Resolving with placeholders and substituting the real
    values into the request body afterwards keeps secrets out of ARM entirely.
    """

    secure_names = _secure_parameter_names(template)
    if not secure_names:
        return parameters, {}

    masked = json.loads(json.dumps(parameters))
    values = masked.get("parameters") or {}
    secrets: dict[str, str] = {}

    for index, name in enumerate(sorted(secure_names)):
        entry = values.get(name)
        if not isinstance(entry, dict) or "value" not in entry:
            continue
        value = entry["value"]
        if not isinstance(value, str):
            raise RuntimeError(
                f"Parameter '{name}' is a secureObject, which is not supported with "
                "--flights. Use a securestring so its value can be kept out of the "
                "resolver deployment."
            )
        sentinel = f"__caci_secret_{index}__"
        secrets[sentinel] = value
        entry["value"] = sentinel

    return masked, secrets


def _warn_unresolved_secrets(resolved: list[dict], secrets: dict[str, str]):
    """Warn when a secure parameter did not survive resolution verbatim.

    Inspects only the sentinel-bearing structures, never the secret values, so the
    resolved resources stay free of sensitive data.
    """

    if not secrets:
        return

    serialised = json.dumps(resolved)
    for sentinel in secrets:
        if sentinel not in serialised:
            print(
                "Warning: a secure parameter did not reach the request body verbatim, so its "
                "value will not be substituted. A template that transforms it - with base64() "
                "or concat(), for example - cannot be used with --flights.",
                file=sys.stderr,
                flush=True,
            )


def _inject_secrets(body: str, secrets: dict[str, str]) -> str:
    """Substitute real secret values into an already serialised request body.

    Deliberately narrow: secrets are placed only into the string written to the
    request body file, and never back into the resolved resource structures, which
    are logged, iterated and polled.
    """

    for sentinel, value in secrets.items():
        body = body.replace(sentinel, json.dumps(value)[1:-1])
    return body


def _az_rest(method: str, url: str, subscription: str, headers: list[str], body_file: str | None) -> dict | None:
    command = ["az", "rest", "--method", method, "--url", url, "--subscription", subscription]
    if headers:
        command += ["--headers", *headers]
    if body_file:
        command += ["--body", f"@{body_file}"]
    output = _run(command, f"{method.upper()} {url.split('?')[0].split('/')[-1]}")
    output = output.strip()
    return json.loads(output) if output else None


def _print_events(resource_state: dict | None):
    if not resource_state:
        return
    events = (resource_state.get("properties", {}).get("instanceView", {}) or {}).get("events") or []
    for event in events:
        print(
            f"  [{event.get('type', '')}] {event.get('name', '')}: {event.get('message', '')}",
            flush=True,
        )


def deploy_flighted(
    template: dict,
    parameters: dict,
    deployment_name: str,
    subscription: str,
    resource_group: str,
    flights: str,
    timeout: int,
) -> tuple[list[str], str]:
    """Resolve `template` through ARM then PUT each resource with the flight header.

    Returns the deployment's `ids` output and the resolver deployment's correlation ID.
    """

    resources = _resource_list(template)
    if not resources:
        raise RuntimeError("Target template declares no resources to deploy")

    blocked = _find_runtime_references(resources) + _find_runtime_references(template.get("outputs") or {})
    if blocked:
        raise RuntimeError(
            "Cannot deploy with --flights because the template uses runtime references "
            "that ARM can only evaluate once its resources exist:"
            + os.linesep
            + os.linesep.join(f"  {expression}" for expression in blocked)
        )

    with tempfile.TemporaryDirectory() as temp_dir:
        resolver_path = os.path.join(temp_dir, "resolver.json")
        with open(resolver_path, "w") as f:
            json.dump(_build_resolver_template(template, resources), f)

        parameters_file = os.path.join(temp_dir, "parameters.json")
        masked_parameters, secrets = _mask_secure_parameters(template, parameters)
        with open(parameters_file, "w") as f:
            json.dump(masked_parameters, f)

        print(f"Resolving {len(resources)} resource(s) through ARM...", flush=True)
        result = json.loads(
            _run(
                [
                    "az", "deployment", "group", "create",
                    "-n", deployment_name,
                    "--subscription", subscription,
                    "--resource-group", resource_group,
                    "--template-file", resolver_path,
                    "--parameters", f"@{parameters_file}",
                    "-o", "json",
                ],
                "Resolving template",
            )
        )

        outputs = result.get("properties", {}).get("outputs", {}) or {}
        correlation_id = result.get("properties", {}).get("correlationId", "") or ""
        resolved = outputs.get(RESOLVED_RESOURCES_OUTPUT, {}).get("value") or []
        ids = outputs.get("ids", {}).get("value") or []

        _warn_unresolved_secrets(resolved, secrets)

        for resource in resolved:
            url = _resource_url(subscription, resource_group, resource)
            headers = ["Content-Type=application/json"]
            if resource["type"].lower().startswith(ACI_PROVIDER + "/"):
                headers.insert(0, f"{FLIGHT_HEADER}={flights}")
                print(f"Deploying {resource['name']} with flights '{flights}'", flush=True)
            else:
                print(f"Deploying {resource['name']}", flush=True)

            # Secrets enter the payload only here, immediately before the request,
            # and only inside a private temporary directory that is removed on exit.
            body_path = os.path.join(temp_dir, "body.json")
            with open(body_path, "w") as f:
                f.write(_inject_secrets(json.dumps(_resource_body(resource)), secrets))

            _az_rest("put", url, subscription, headers, body_path)

    _wait_for_resources(resolved, subscription, resource_group, timeout)
    return ids, correlation_id


def _wait_for_resources(resources: list[dict], subscription: str, resource_group: str, timeout: int):
    start_time = time.time()

    for resource in resources:
        url = _resource_url(subscription, resource_group, resource)
        name = resource["name"]
        state = None
        latest = None

        while True:
            latest = _az_rest("get", url, subscription, [], None)
            state = (latest or {}).get("properties", {}).get("provisioningState", "")
            if state in TERMINAL_STATES:
                break
            if timeout > 0 and (time.time() - start_time) >= timeout:
                _print_events(latest)
                raise RuntimeError(
                    f"Deployment of {name} timed out after {timeout}s in state '{state}'"
                )
            time.sleep(15)

        if state != "Succeeded":
            print(f"{name} finished in state '{state}'", flush=True)
            _print_events(latest)
            raise RuntimeError(f"Deployment of {name} failed with provisioningState '{state}'")

        print(f"{name} succeeded", flush=True)
        sys.stdout.flush()
