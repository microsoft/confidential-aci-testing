#!/usr/bin/env python3

# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.


import argparse
import json
import json5
import os


def vscode_testing(target):

    with open(os.path.join(os.path.dirname(__file__), ".vscode", "launch.json"), "r") as file:
        launch_json = json5.load(file)

    user_json_path = os.path.join(os.curdir, ".vscode", "launch.json")
    def dump_to_user_json(json_data):
        with open(user_json_path, "w") as file:
            json.dump(json_data, file, indent=4)

    if not os.path.exists(user_json_path):
        dump_to_user_json(launch_json)
        return

    with open(os.path.join(os.curdir, ".vscode", "launch.json"), "r") as file:
        user_json = json5.load(file)

    existing_configurations = {configuration["name"] for configuration in user_json["configurations"]}
    existing_inputs = {input["id"] for input in user_json["inputs"]}

    for configuration in launch_json["configurations"]:
        if configuration["name"] not in existing_configurations:
            user_json["configurations"].append(configuration)

    for input in launch_json["inputs"]:
        if input["id"] not in existing_inputs:
            user_json["inputs"].append(input)

    dump_to_user_json(user_json)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add python test target")

    parser.add_argument("target",
        help="Target directory", default=os.environ.get("TARGET"),
        nargs="?", # aka Optional
        type=lambda path: os.path.abspath(os.path.expanduser(path)))

    args = parser.parse_args()

    vscode_testing(args.target)
