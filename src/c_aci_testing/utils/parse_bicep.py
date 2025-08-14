#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations

import json
import subprocess
import sys
from typing import Iterable, Tuple, Any, Dict, List

from c_aci_testing.tools.aci_param_set import aci_param_set
from c_aci_testing.utils.find_bicep import find_bicep_files
from c_aci_testing.utils.arm_expression import evaluate_expr


def _resolve_arm_functions(
    templateJson: Dict[str, Any], parametersJson: Dict[str, Any], resource_group, subscription, deployment_name
):
    parameters_defaults_dict = {
        key: value.get("defaultValue", None) for key, value in templateJson["parameters"].items()
    }
    parameters_dict = {key: value["value"] for key, value in parametersJson["parameters"].items()}
    parameters = {}
    parameters.update(parameters_defaults_dict)
    parameters.update(parameters_dict)

    def _handle_func(func_name: str, args: List[Any]) -> Any:
        """
        Handle ARM functions. All args are already evaluated
        """
        if func_name == "concat":
            assert all(isinstance(arg, str) for arg in args)
            return "".join(args)
        elif func_name == "subscription":
            return {
                "subscriptionId": subscription,
            }
        elif func_name == "resourceGroup":
            return {
                "name": resource_group,
            }
        elif func_name == "deployment":
            return {
                "name": deployment_name,
            }
        elif func_name == "resourceId":
            assert all(isinstance(arg, str) for arg in args)
            if len(args) == 3:
                return f"/subscriptions/{subscription}/resourceGroups/{args[0]}/providers/{args[1]}/{args[2]}"
            elif len(args) == 2:
                return f"/subscriptions/{subscription}/resourceGroups/{resource_group}/providers/{args[0]}/{args[1]}"
        elif func_name == "parameters":
            assert len(args) == 1 and isinstance(args[0], str)
            if args[0] not in parameters:
                raise ValueError(f"Invalid parameter: {args[0]}")
            return parameters[args[0]]
        elif func_name == "if":
            assert len(args) == 3
            assert isinstance(args[0], bool)
            if args[0]:
                return args[1]
            else:
                return args[2]
        elif func_name == "empty":
            assert len(args) == 1 and isinstance(args[0], str)
            return args[0] == ""
        elif func_name == "format":
            assert len(args) >= 1
            assert isinstance(args[0], str)
            format_string = args[0]
            inputs = args[1:]
            # Handle the case where inputs are not strings
            # Convert all inputs to strings
            inputs = [str(arg) for arg in inputs]
            # Format the string
            return format_string.format(*inputs)
        elif func_name == "add":
            assert len(args) == 2
            assert isinstance(args[0], (int, float))
            assert isinstance(args[1], (int, float))
            return args[0] + args[1]
        elif func_name == "sub":
            assert len(args) == 2
            assert isinstance(args[0], (int, float))
            assert isinstance(args[1], (int, float))
            return args[0] - args[1]
        elif func_name == "not":
            assert len(args) == 1
            assert isinstance(args[0], bool)
            return not args[0]
        elif func_name == "createObject":
            obj = {}
            for i in range(0, len(args), 2):
                if i + 1 >= len(args):
                    raise ValueError("createObject requires an even number of arguments")
                key = args[i]
                value = args[i + 1]
                assert isinstance(key, str)
                obj[key] = value
            return obj
        elif func_name == "createArray":
            return args
        elif func_name == "equals":
            assert len(args) == 2
            return args[0] == args[1]
        else:
            ret_str = f"{func_name}("
            first = True
            for arg in args:
                if first:
                    first = False
                else:
                    ret_str += ","
                if isinstance(arg, str):
                    ret_str += f"'{arg}'"
                else:
                    ret_str += repr(arg)
            ret_str += ")"
            print(f"Warning: Unknown function: {ret_str}", file=sys.stderr, flush=True)
            return ret_str

    def _resolve_val(val: Any) -> Any:
        if isinstance(val, str) and val.startswith("[") and val.endswith("]"):
            return evaluate_expr(val[1:-1], _handle_func)
        elif isinstance(val, list):
            return [_resolve_val(v) for v in val]
        elif isinstance(val, dict):
            return {_resolve_val(k): _resolve_val(v) for k, v in val.items()}
        else:
            return val

    for k in parameters.keys():
        parameters[k] = _resolve_val(parameters[k])

    return _resolve_val(templateJson)


def parse_bicep(
    target_path: str,
    subscription: str,
    resource_group: str,
    deployment_name: str,
    registry: str,
    repository: str | None,
    tag: str | None,
) -> dict:
    """
    Returns ARM template JSON with parameters inlined
    """

    _, bicepparam_file_path = find_bicep_files(target_path)

    # Set required parameters in bicep param file
    aci_param_set(
        target_path,
        parameters={
            "registry": registry,
            "repository": repository or "",
            "tag": tag or "",
        },
        add=False,  # If the user removed a field, don't re-add it
    )

    print("Converting bicep files to an ARM template", flush=True)
    sys.stderr.flush()
    res = subprocess.run(
        [
            "az",
            "bicep",
            "build-params",
            "--file",
            bicepparam_file_path,
            "--stdout",
        ],
        check=True,
        stdout=subprocess.PIPE,
    )
    res_json = json.loads(res.stdout.decode())
    arm_template_json = _resolve_arm_functions(
        json.loads(res_json["templateJson"]),
        json.loads(res_json["parametersJson"]),
        resource_group=resource_group,
        subscription=subscription,
        deployment_name=deployment_name,
    )

    return arm_template_json


def arm_template_for_each_container_group(
    arm_template_json: dict,
) -> Iterable[Tuple[dict, Iterable[dict]]]:
    """
    Return an iterater of tuples:
        (container_group_resource_json, containers)
    where:
        - container_group_resource_json is the ARM JSON for a container group
        - containers is an iterable of the containers in the container group
    """

    for resource in arm_template_json["resources"]:
        # Only handle container groups
        if resource["type"] not in (
            "Microsoft.ContainerInstance/containerGroups",
            "Microsoft.ContainerInstance/containerGroupProfiles",
        ):
            continue

        def get_containers(group) -> Iterable[dict]:
            if "containers" in group["properties"]:
                for container in group["properties"]["containers"]:
                    yield container

        yield resource, get_containers(resource)


def arm_template_for_each_container_group_with_fixup(
    arm_template_json: dict,
) -> Iterable[Tuple[dict, Iterable[dict]]]:
    """
    Same interface as arm_template_for_each_container_group, but with some
    acipolicygen workarounds
    """

    for resource, containers in arm_template_for_each_container_group(arm_template_json):

        containers = list(containers)

        # Workaround for acipolicygen not supporting empty environment variables
        for container in containers:
            for env_var in container["properties"].get("environmentVariables", []):
                if "value" in env_var and env_var["value"] == "":
                    del env_var["value"]
                if "value" not in env_var:
                    env_var["secureValue"] = ""

        yield resource, containers
